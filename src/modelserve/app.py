"""FastAPI application factory, lifespan management, and API routes."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from modelserve.logging import setup_logging
from modelserve.middleware import (
    AccessLoggingMiddleware,
    PayloadLimitMiddleware,
    RequestIDMiddleware,
)
from modelserve.model_loader import (
    ArtifactError,
    LoadedModel,
    load_active_model,
)
from modelserve.schemas import (
    ErrorResponse,
    HealthLiveResponse,
    HealthReadyResponse,
    ModelInfoResponse,
    ModelMetadata,
    PredictionOutput,
    PredictionRequest,
    PredictionResponse,
)
from modelserve.settings import Settings, get_settings

logger = logging.getLogger("modelserve.app")


def _get_request_id(request: Request) -> str:
    """Retrieve the assigned request ID from request state, or fallback."""
    return getattr(request.state, "request_id", "unknown_request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: verifies and loads the active model once at startup."""
    settings: Settings = getattr(app.state, "settings", get_settings())
    setup_logging(settings.log_level)
    logger.info("Starting ModelServe AI service in %s environment", settings.env)

    app.state.model = None
    app.state.is_ready = False
    app.state.ready_error = None

    try:
        loaded_model = load_active_model(
            artifacts_dir=settings.artifacts_dir,
            version=settings.model_version,
        )
        app.state.model = loaded_model
        app.state.is_ready = True
        logger.info(
            "ModelServe AI is ready. Active model: %s (version: %s)",
            loaded_model.name,
            loaded_model.version,
        )
    except ArtifactError as exc:
        app.state.ready_error = str(exc)
        logger.error("Model initialization failed: %s", exc)
    except Exception as exc:
        app.state.ready_error = f"Unexpected failure during model load: {exc}"
        logger.exception("Unexpected exception loading model artifact: %s", exc)

    yield

    logger.info("Shutting down ModelServe AI service")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title="ModelServe AI",
        description=(
            "Production-oriented ML inference service. Serves customer churn predictions "
            "with validated schemas, request tracking, and trusted model artifacts."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    # Middleware order: outermost first
    app.add_middleware(AccessLoggingMiddleware)
    app.add_middleware(PayloadLimitMiddleware, max_payload_bytes=app_settings.max_payload_bytes)
    app.add_middleware(RequestIDMiddleware)

    # --------------------------------------------------------------------------
    # Exception Handlers
    # --------------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning(
            "Validation error on %s %s: %s",
            request.method,
            request.url.path,
            exc.errors(),
            extra={"request_id": request_id},
        )
        details = [
            {
                "loc": [str(loc_item) for loc_item in err.get("loc", [])],
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        http_422 = getattr(
            status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        return JSONResponse(
            status_code=http_422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request does not match the required input schema.",
                    "request_id": request_id,
                    "details": details,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        code_map = {
            400: "BAD_REQUEST",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "PAYLOAD_TOO_LARGE",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.exception(
            "Unhandled server error on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    # --------------------------------------------------------------------------
    # Health Routes
    # --------------------------------------------------------------------------

    @app.get(
        "/health/live",
        response_model=HealthLiveResponse,
        tags=["Health"],
        summary="Service liveness check",
        responses={200: {"model": HealthLiveResponse}},
    )
    async def health_live() -> HealthLiveResponse:
        """Indicates that the application process is running."""
        return HealthLiveResponse(status="alive")

    @app.get(
        "/health/ready",
        response_model=HealthReadyResponse,
        tags=["Health"],
        summary="Service readiness check",
        responses={
            200: {"model": HealthReadyResponse},
            503: {"model": ErrorResponse, "description": "Model not loaded or invalid"},
        },
    )
    async def health_ready(request: Request) -> Any:
        """Indicates whether the service is ready to accept predictions."""
        if not getattr(app.state, "is_ready", False) or app.state.model is None:
            request_id = _get_request_id(request)
            error_reason = getattr(app.state, "ready_error", "Model artifact not loaded")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable: {error_reason}",
            )

        return HealthReadyResponse(
            status="ready",
            model_version=app.state.model.version,
        )

    # --------------------------------------------------------------------------
    # Model Routes
    # --------------------------------------------------------------------------

    @app.get(
        "/v1/model/info",
        response_model=ModelInfoResponse,
        tags=["Model"],
        summary="Active model metadata and provenance",
        responses={
            200: {"model": ModelInfoResponse},
            503: {"model": ErrorResponse, "description": "Service not ready"},
        },
    )
    async def model_info(request: Request) -> ModelInfoResponse:
        """Returns the active model's name, version, feature schema, and evaluation metrics."""
        model: LoadedModel | None = getattr(app.state, "model", None)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model is not loaded or verified",
            )

        manifest = model.manifest
        return ModelInfoResponse(
            name=model.name,
            version=model.version,
            created_at_utc=manifest.get("created_at_utc", ""),
            dataset=manifest.get("dataset", {}),
            feature_schema=manifest.get("feature_schema", {}),
            feature_columns=model.feature_columns,
            positive_label=model.positive_label,
            test_metrics=manifest.get("test_metrics", {}),
            score_interpretation=model.score_interpretation,
        )

    @app.post(
        "/v1/predictions",
        response_model=PredictionResponse,
        tags=["Inference"],
        summary="Predict customer churn for a single observation",
        responses={
            200: {"model": PredictionResponse},
            413: {"model": ErrorResponse, "description": "Payload too large"},
            422: {"model": ErrorResponse, "description": "Input schema validation error"},
            503: {"model": ErrorResponse, "description": "Service not ready"},
        },
    )
    async def predict_churn(request: Request, payload: PredictionRequest) -> PredictionResponse:
        """Accepts a single customer record and predicts churn label and probability score."""
        model: LoadedModel | None = getattr(app.state, "model", None)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model is not loaded or verified",
            )

        request_id = _get_request_id(request)

        # Convert Pydantic features to DataFrame for sklearn pipeline
        features_dict = payload.features.model_dump()
        features_df = pd.DataFrame([features_dict])

        label, score = model.predict(features_df)

        return PredictionResponse(
            request_id=request_id,
            model=ModelMetadata(name=model.name, version=model.version),
            prediction=PredictionOutput(label=label, score=score),
            status="success",
        )

    return app


app = create_app()


def run() -> None:
    """CLI entry point for running the API server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "modelserve.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()

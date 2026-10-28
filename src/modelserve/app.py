"""FastAPI application factory, lifespan management, and API routes."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from modelserve.database import check_database_connection, get_engine, get_session_factory, init_db
from modelserve.logging import setup_logging
from modelserve.middleware import (
    AccessLoggingMiddleware,
    PayloadLimitMiddleware,
    PayloadTooLargeError,
    RequestIDMiddleware,
)
from modelserve.model_loader import (
    ArtifactError,
    LoadedModel,
    load_active_model,
)
from modelserve.repository import (
    get_monitoring_summary,
    record_prediction,
    upsert_model_version,
)
from modelserve.schemas import (
    ErrorResponse,
    HealthLiveResponse,
    HealthReadyResponse,
    ModelInfoResponse,
    ModelMetadata,
    MonitoringSummaryResponse,
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
    """Application lifespan context: initializes model and database connection at startup."""
    settings: Settings = getattr(app.state, "settings", get_settings())
    setup_logging(settings.log_level)
    logger.info("Starting ModelServe AI service in %s environment", settings.env)

    app.state.model = None
    app.state.is_ready = False
    app.state.ready_error = None
    app.state.db_engine = None
    app.state.session_factory = None
    app.state.db_connected = False

    # Initialize Database if configured
    if settings.database_url:
        try:
            engine = get_engine(settings.database_url)
            app.state.db_engine = engine
            app.state.session_factory = get_session_factory(engine)
            # Bootstrap tables directly if using sqlite for tests/dev
            if settings.database_url.startswith("sqlite"):
                init_db(engine)
            app.state.db_connected = check_database_connection(engine)
            if app.state.db_connected:
                # Ensure schema exists on startup if database is available
                init_db(engine)
            logger.info("Database connection initialized. Connected: %s", app.state.db_connected)
        except Exception as exc:
            logger.warning("Database setup failed: %s", exc)

    # Initialize Model
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

        # Register model metadata in database if connected
        if app.state.db_connected and app.state.session_factory:
            try:
                with app.state.session_factory() as session:
                    upsert_model_version(
                        session,
                        version=loaded_model.version,
                        name=loaded_model.name,
                        artifact_sha256=loaded_model.manifest["artifact_sha256"],
                        dataset_fingerprint=loaded_model.manifest.get("dataset", {}).get("sha256", "unknown"),
                        created_at_utc=datetime.now(UTC),
                        manifest=loaded_model.manifest,
                    )
                logger.info("Model version %s registered in database", loaded_model.version)
            except Exception as exc:
                logger.warning("Failed to register model version in database: %s", exc)

    except ArtifactError as exc:
        app.state.ready_error = str(exc)
        logger.error("Model initialization failed: %s", exc)
    except Exception as exc:
        app.state.ready_error = f"Unexpected failure during model load: {exc}"
        logger.exception("Unexpected exception loading model artifact: %s", exc)

    yield

    logger.info("Shutting down ModelServe AI service")
    if getattr(app.state, "db_engine", None):
        app.state.db_engine.dispose()


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

    cors_origins = app_settings.cors_origins
    has_wildcard = "*" in cors_origins or any("*" in o for o in cors_origins)
    if has_wildcard:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )

    # --------------------------------------------------------------------------
    # Exception Handlers
    # --------------------------------------------------------------------------

    @app.exception_handler(PayloadTooLargeError)
    async def payload_too_large_exception_handler(
        request: Request, exc: PayloadTooLargeError
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": str(exc.detail if hasattr(exc, "detail") else exc),
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = _get_request_id(request)

        # Sanitize logged representation: log only types and locations, never raw input values
        sanitized_log = [
            {
                "loc": [str(loc_item) for loc_item in err.get("loc", [])],
                "type": err.get("type", "validation_error"),
            }
            for err in exc.errors()
        ]
        logger.warning(
            "Validation error on %s %s: %s",
            request.method,
            request.url.path,
            sanitized_log,
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

        # Handle PayloadTooLargeError wrapped inside ExceptionGroup by BaseHTTPMiddleware
        cause = getattr(exc, "__cause__", None)
        if cause is not None:
            if isinstance(cause, PayloadTooLargeError):
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": str(cause.detail),
                            "request_id": request_id,
                        }
                    },
                    headers={"X-Request-ID": request_id},
                )
            if hasattr(cause, "exceptions"):
                for sub_exc in getattr(cause, "exceptions", []):
                    if isinstance(sub_exc, PayloadTooLargeError):
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": {
                                    "code": "PAYLOAD_TOO_LARGE",
                                    "message": str(sub_exc.detail),
                                    "request_id": request_id,
                                }
                            },
                            headers={"X-Request-ID": request_id},
                        )

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
            logger.error(
                "Readiness probe failed: %s",
                error_reason,
                extra={"request_id": request_id},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable: model is not ready to serve predictions.",
            )

        db_connected = bool(getattr(app.state, "db_connected", False))
        if getattr(app.state, "db_engine", None):
            db_connected = check_database_connection(app.state.db_engine)
            app.state.db_connected = db_connected

        return HealthReadyResponse(
            status="ready",
            model_version=app.state.model.version,
            database_connected=db_connected,
        )

    # --------------------------------------------------------------------------
    # Model & Monitoring Routes
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
        """Accepts a single customer record, predicts churn outcome, and records telemetry."""
        model: LoadedModel | None = getattr(app.state, "model", None)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model is not loaded or verified",
            )

        request_id = _get_request_id(request)
        start_time = time.perf_counter()

        # Convert Pydantic features to DataFrame for sklearn pipeline
        features_dict = payload.features.model_dump()
        features_df = pd.DataFrame([features_dict])

        label, score = model.predict(features_df)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Durable telemetry persistence (raw features are omitted per ADR-008)
        session_factory = getattr(app.state, "session_factory", None)
        if session_factory:
            try:
                with session_factory() as session:
                    record_prediction(
                        session,
                        request_id=request_id,
                        model_version=model.version,
                        label=label,
                        score=score,
                        latency_ms=latency_ms,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to persist prediction event to database: %s",
                    exc,
                    extra={"request_id": request_id},
                )

        return PredictionResponse(
            request_id=request_id,
            model=ModelMetadata(name=model.name, version=model.version),
            prediction=PredictionOutput(label=label, score=score),
            status="success",
        )

    @app.get(
        "/v1/monitoring/summary",
        response_model=MonitoringSummaryResponse,
        tags=["Monitoring"],
        summary="Aggregated inference activity over a rolling time window",
        responses={
            200: {"model": MonitoringSummaryResponse},
            503: {"model": ErrorResponse, "description": "Database store unavailable"},
        },
    )
    async def monitoring_summary(
        request: Request,
        window_hours: int = Query(default=24, ge=1, le=720, description="Rolling time window in hours"),
        model_version: str | None = Query(default=None, description="Filter summary by model version"),
    ) -> MonitoringSummaryResponse:
        """Returns bounded-window inference statistics (label distribution, latency percentiles)."""
        session_factory = getattr(app.state, "session_factory", None)
        if not session_factory:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Persistence store is not configured or unavailable",
            )

        try:
            with session_factory() as session:
                summary = get_monitoring_summary(
                    session,
                    window_hours=window_hours,
                    model_version=model_version,
                )
            return MonitoringSummaryResponse(**summary)
        except Exception as exc:
            logger.error("Failed to query monitoring summary: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database query failed during monitoring summary retrieval",
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

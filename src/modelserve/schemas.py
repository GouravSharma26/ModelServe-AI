"""Pydantic validation schemas for API requests, responses, and error contracts."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CustomerFeatures(BaseModel):
    """Documented input features for Telco Customer Churn inference.

    Extra fields are strictly forbidden by schema policy to prevent silent misuse.
    """

    model_config = ConfigDict(extra="forbid")

    gender: Literal["Female", "Male"] = Field(
        description="Customer gender ('Female' or 'Male')"
    )
    SeniorCitizen: Literal[0, 1] = Field(
        description="Whether the customer is a senior citizen (1) or not (0)"
    )
    Partner: Literal["Yes", "No"] = Field(
        description="Whether the customer has a partner ('Yes' or 'No')"
    )
    Dependents: Literal["Yes", "No"] = Field(
        description="Whether the customer has dependents ('Yes' or 'No')"
    )
    tenure: int = Field(
        ge=0,
        description="Number of months the customer has stayed with the company",
    )
    PhoneService: Literal["Yes", "No"] = Field(
        description="Whether the customer has a phone service ('Yes' or 'No')"
    )
    MultipleLines: Literal["No phone service", "No", "Yes"] = Field(
        description="Whether the customer has multiple lines"
    )
    InternetService: Literal["DSL", "Fiber optic", "No"] = Field(
        description="Customer’s internet service provider"
    )
    OnlineSecurity: Literal["No internet service", "No", "Yes"] = Field(
        description="Whether the customer has online security"
    )
    OnlineBackup: Literal["No internet service", "No", "Yes"] = Field(
        description="Whether the customer has online backup"
    )
    DeviceProtection: Literal["No internet service", "No", "Yes"] = Field(
        description="Whether the customer has device protection"
    )
    TechSupport: Literal["No internet service", "No", "Yes"] = Field(
        description="Whether the customer has tech support"
    )
    StreamingTV: Literal["No internet service", "No", "Yes"] = Field(
        description="Whether the customer has streaming TV"
    )
    StreamingMovies: Literal["No internet service", "No", "Yes"] = Field(
        description="Whether the customer has streaming movies"
    )
    Contract: Literal["Month-to-month", "One year", "Two year"] = Field(
        description="The contract term of the customer"
    )
    PaperlessBilling: Literal["Yes", "No"] = Field(
        description="Whether the customer has paperless billing"
    )
    PaymentMethod: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ] = Field(description="The customer’s payment method")
    MonthlyCharges: float = Field(
        ge=0.0,
        description="The amount charged to the customer monthly",
    )
    TotalCharges: float | None = Field(
        default=None,
        ge=0.0,
        description="Total amount charged; can be null for zero-tenure customers (imputed during preprocessing)",
    )


class PredictionRequest(BaseModel):
    """Single-record inference request body."""

    model_config = ConfigDict(extra="forbid")

    features: CustomerFeatures


class ModelMetadata(BaseModel):
    """Identification metadata for the active model."""

    name: str
    version: str


class PredictionOutput(BaseModel):
    """Classification outcome and raw model score."""

    label: Literal["Yes", "No"]
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated score for positive class 'Yes' (uncalibrated probability)",
    )


class PredictionResponse(BaseModel):
    """Standardized response contract for /v1/predictions."""

    request_id: str
    model: ModelMetadata
    prediction: PredictionOutput
    status: Literal["success"] = "success"


class ModelInfoResponse(BaseModel):
    """Detailed metadata for /v1/model/info."""

    name: str
    version: str
    created_at_utc: str
    dataset: dict[str, Any]
    feature_schema: dict[str, list[str]]
    feature_columns: list[str]
    positive_label: str
    test_metrics: dict[str, Any]
    score_interpretation: str


class HealthLiveResponse(BaseModel):
    """Response contract for /health/live."""

    status: Literal["alive"] = "alive"


class HealthReadyResponse(BaseModel):
    """Response contract for /health/ready."""

    status: Literal["ready"] = "ready"
    model_version: str
    database_connected: bool = True


class ScoreSummary(BaseModel):
    """Aggregated prediction score statistics."""

    mean: float
    min: float
    max: float


class LatencySummary(BaseModel):
    """Inference execution latency percentiles in milliseconds."""

    mean: float
    p50: float
    p90: float
    p95: float
    p99: float


class MonitoringSummaryResponse(BaseModel):
    """Bounded-window inference activity summary for /v1/monitoring/summary."""

    window_hours: int
    window_start_utc: str
    window_end_utc: str
    model_version: str | None = None
    total_predictions: int
    label_distribution: dict[str, int]
    score_summary: ScoreSummary
    latency_summary_ms: LatencySummary


class ErrorDetail(BaseModel):
    """Structured error object conforming to the API Guide error contract."""

    code: str
    message: str
    request_id: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    """Unified error envelope."""

    error: ErrorDetail

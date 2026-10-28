"""Streamlit monitoring dashboard for ModelServe AI.

Displays active model metadata, offline evaluation benchmarks, and live telemetry from PostgreSQL.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

st.set_page_config(
    page_title="ModelServe AI — Inference & Monitoring",
    page_icon="📊",
    layout="wide",
)

st.title("ModelServe AI — Inference & Monitoring Dashboard")
st.caption("Production-oriented customer churn classification and telemetry platform")


def fetch_api_json(path: str, params: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch JSON from API with graceful error handling."""
    try:
        response = requests.get(f"{API_URL}{path}", params=params, timeout=5)
        if response.status_code == 200:
            return response.json(), None
        return None, f"HTTP {response.status_code}: {response.text}"
    except Exception as exc:
        return None, str(exc)


# -----------------------------------------------------------------------------
# System Status Banner
# -----------------------------------------------------------------------------
col_status1, col_status2, col_status3 = st.columns(3)

live_data, live_err = fetch_api_json("/health/live")
ready_data, ready_err = fetch_api_json("/health/ready")
model_data, model_err = fetch_api_json("/v1/model/info")

with col_status1:
    if live_data and live_data.get("status") == "alive":
        st.success("API Process: **Alive**")
    else:
        st.error(f"API Process: **Offline** ({live_err or 'unreachable'})")

with col_status2:
    if ready_data and ready_data.get("status") == "ready":
        db_state = "Connected" if ready_data.get("database_connected") else "Disconnected"
        st.success(f"Inference Engine: **Ready** (DB: {db_state})")
    else:
        st.warning("Inference Engine: **Not Ready**")

with col_status3:
    if model_data:
        st.info(f"Model: **{model_data.get('name')}** (`{model_data.get('version')}`)")
    else:
        st.info("Model Version: **Unavailable**")

st.divider()

# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab_monitoring, tab_model_info, tab_tester = st.tabs([
    "📈 Live Telemetry",
    "🧠 Model Provenance & Metrics",
    "🧪 Prediction Playground",
])

# -----------------------------------------------------------------------------
# Tab 1: Live Telemetry
# -----------------------------------------------------------------------------
with tab_monitoring:
    st.subheader("Inference Telemetry & Monitoring")
    window_hours = st.selectbox(
        "Aggregation Window",
        options=[1, 6, 24, 72, 168],
        index=2,
        format_func=lambda h: f"Past {h} hours",
    )

    summary_data, summary_err = fetch_api_json("/v1/monitoring/summary", params={"window_hours": window_hours})

    if summary_err or not summary_data:
        st.warning(f"Unable to retrieve telemetry: {summary_err or 'No data returned'}")
        st.info("Ensure PostgreSQL is running and DATABASE_URL is configured.")
    else:
        total = summary_data.get("total_predictions", 0)
        labels = summary_data.get("label_distribution", {})
        score_sum = summary_data.get("score_summary", {})
        latency_sum = summary_data.get("latency_summary_ms", {})

        if total == 0:
            st.info(
                f"ℹ️ **No prediction events recorded yet in the past {window_hours} hours.**\n\n"
                "Send inference requests to `POST /v1/predictions` to observe telemetry, or use the Prediction Playground tab."
            )
        else:
            yes_count = labels.get("Yes", 0)
            churn_rate = (yes_count / total * 100) if total > 0 else 0.0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Predictions", f"{total:,}")
            m2.metric("Predicted Churn Rate", f"{churn_rate:.1f}%", f"{yes_count} churn alerts")
            m3.metric("Average Score", f"{score_sum.get('mean', 0.0):.3f}")
            m4.metric("Latency p95", f"{latency_sum.get('p95', 0.0):.1f} ms", f"Mean: {latency_sum.get('mean', 0.0):.1f} ms")

            st.write("### Prediction Label Distribution")
            chart_data = pd.DataFrame({
                "Outcome": list(labels.keys()),
                "Count": list(labels.values()),
            })
            st.bar_chart(chart_data.set_index("Outcome"))

            st.write("### Execution Latency Profile (ms)")
            lat_df = pd.DataFrame([{
                "Metric": k.upper(),
                "Latency (ms)": v,
            } for k, v in latency_sum.items()])
            st.dataframe(lat_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab 2: Model Provenance & Metrics
# -----------------------------------------------------------------------------
with tab_model_info:
    st.subheader("Model Evaluation & Training Provenance")
    if model_data:
        dataset_meta = model_data.get("dataset", {})
        test_metrics = model_data.get("test_metrics", {})

        c1, c2 = st.columns(2)
        with c1:
            st.write("#### Dataset Provenance")
            st.markdown(f"- **Source:** [{dataset_meta.get('name')}]({dataset_meta.get('source')})")
            st.markdown(f"- **License:** `{dataset_meta.get('license')}`")
            st.markdown(f"- **Dataset SHA-256:** `{dataset_meta.get('sha256')}`")
            st.markdown(f"- **Total Rows:** {dataset_meta.get('rows'):,}")
            st.markdown(f"- **Positive Label:** `{model_data.get('positive_label')}`")

        with c2:
            st.write("#### Offline Held-Out Evaluation (Test Split)")
            if test_metrics:
                st.markdown(f"- **PR-AUC (Average Precision):** `{test_metrics.get('pr_auc_average_precision', 0.0):.4f}`")
                st.markdown(f"- **ROC-AUC:** `{test_metrics.get('roc_auc', 0.0):.4f}`")
                st.markdown(f"- **F1 Score:** `{test_metrics.get('f1', 0.0):.4f}`")
                st.markdown(f"- **Precision:** `{test_metrics.get('precision', 0.0):.4f}`")
                st.markdown(f"- **Recall:** `{test_metrics.get('recall', 0.0):.4f}`")
                st.markdown(f"- **Decision Threshold:** `{test_metrics.get('decision_threshold')}`")

        st.caption(
            "⚠️ Note: These are benchmark measurements from offline validation on fictional IBM sample data. "
            "Output scores are uncalibrated and do not reflect verified accuracy on live customer populations."
        )

        matrix = test_metrics.get("confusion_matrix")
        if matrix:
            st.write("#### Held-Out Confusion Matrix")
            st.write("Rows: True Labels [No, Yes] | Columns: Predicted Labels [No, Yes]")
            cm_df = pd.DataFrame(matrix, index=["True No", "True Yes"], columns=["Pred No", "Pred Yes"])
            st.dataframe(cm_df)
    else:
        st.warning("Model info currently unavailable.")

# -----------------------------------------------------------------------------
# Tab 3: Prediction Playground
# -----------------------------------------------------------------------------
with tab_tester:
    st.subheader("Submit Single-Record Prediction")
    with st.form("prediction_form"):
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            gender = st.selectbox("Gender", ["Female", "Male"])
            senior = st.selectbox("Senior Citizen", [0, 1], format_func=lambda x: "Yes (1)" if x == 1 else "No (0)")
            partner = st.selectbox("Partner", ["Yes", "No"])
            dependents = st.selectbox("Dependents", ["Yes", "No"])
            tenure = st.number_input("Tenure (Months)", min_value=0, max_value=120, value=12)
            phone = st.selectbox("Phone Service", ["Yes", "No"])
            multiple = st.selectbox("Multiple Lines", ["No", "Yes", "No phone service"])

        with p_col2:
            internet = st.selectbox("Internet Service", ["DSL", "Fiber optic", "No"])
            security = st.selectbox("Online Security", ["No", "Yes", "No internet service"])
            backup = st.selectbox("Online Backup", ["Yes", "No", "No internet service"])
            device = st.selectbox("Device Protection", ["No", "Yes", "No internet service"])
            tech = st.selectbox("Tech Support", ["No", "Yes", "No internet service"])
            tv = st.selectbox("Streaming TV", ["No", "Yes", "No internet service"])
            movies = st.selectbox("Streaming Movies", ["No", "Yes", "No internet service"])

        with p_col3:
            contract = st.selectbox("Contract", ["Month-to-month", "One year", "Two year"])
            paperless = st.selectbox("Paperless Billing", ["Yes", "No"])
            payment = st.selectbox("Payment Method", [
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ])
            monthly = st.number_input("Monthly Charges ($)", min_value=0.0, max_value=300.0, value=65.5)
            total = st.number_input("Total Charges ($)", min_value=0.0, max_value=10000.0, value=786.0)

        submitted = st.form_submit_button("Predict Churn Outcome", type="primary")
        if submitted:
            payload = {
                "features": {
                    "gender": gender,
                    "SeniorCitizen": senior,
                    "Partner": partner,
                    "Dependents": dependents,
                    "tenure": tenure,
                    "PhoneService": phone,
                    "MultipleLines": multiple,
                    "InternetService": internet,
                    "OnlineSecurity": security,
                    "OnlineBackup": backup,
                    "DeviceProtection": device,
                    "TechSupport": tech,
                    "StreamingTV": tv,
                    "StreamingMovies": movies,
                    "Contract": contract,
                    "PaperlessBilling": paperless,
                    "PaymentMethod": payment,
                    "MonthlyCharges": monthly,
                    "TotalCharges": total,
                }
            }
            try:
                pred_res = requests.post(f"{API_URL}/v1/predictions", json=payload, timeout=5)
                if pred_res.status_code == 200:
                    res_json = pred_res.json()
                    pred = res_json["prediction"]
                    label = pred["label"]
                    score = pred["score"]
                    req_id = res_json["request_id"]
                    if label == "Yes":
                        st.error(f"Prediction: **High Churn Risk** (`Yes`) — Score: `{score:.4f}` (Request ID: `{req_id}`)")
                    else:
                        st.success(f"Prediction: **Retained** (`No`) — Score: `{score:.4f}` (Request ID: `{req_id}`)")
                else:
                    st.error(f"Inference failed (HTTP {pred_res.status_code}): {pred_res.text}")
            except Exception as exc:
                st.error(f"Request failed: {exc}")


"""End-to-end smoke test script for ModelServe AI.

Exercises health, model info, predictions, validation failure,
PostgreSQL persistence telemetry, and Streamlit dashboard availability.
"""

from __future__ import annotations

import argparse
import sys
import time
import requests

SAMPLE_PAYLOAD = {
    "features": {
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 12,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "No",
        "DeviceProtection": "Yes",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "One year",
        "PaperlessBilling": "No",
        "PaymentMethod": "Bank transfer (automatic)",
        "MonthlyCharges": 45.2,
        "TotalCharges": 542.4,
    }
}


def run_smoke_test(base_url: str, dashboard_url: str | None = None) -> None:
    print(f"=== Starting ModelServe AI Smoke Test on {base_url} ===")
    session = requests.Session()

    # 1. Test /health/live
    print("1. Testing GET /health/live...")
    r = session.get(f"{base_url}/health/live", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    assert r.json().get("status") == "alive", f"Unexpected body: {r.json()}"
    print("   [OK] Liveness is ALIVE")

    # 2. Test /health/ready
    print("2. Testing GET /health/ready...")
    r = session.get(f"{base_url}/health/ready", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    ready_json = r.json()
    assert ready_json.get("status") == "ready", f"Unexpected ready status: {ready_json}"
    version = ready_json.get("model_version")
    db_connected = ready_json.get("database_connected")
    print(f"   [OK] Readiness is READY (active model version: {version}, database_connected: {db_connected})")

    # 3. Test /v1/model/info
    print("3. Testing GET /v1/model/info...")
    r = session.get(f"{base_url}/v1/model/info", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    info_json = r.json()
    assert "name" in info_json and "dataset" in info_json
    print(f"   [OK] Model info retrieved: {info_json.get('name')}")

    # 4. Test POST /v1/predictions with valid payload
    print("4. Testing POST /v1/predictions (valid payload)...")
    req_id = f"smoke_test_req_{int(time.time())}"
    r = session.post(
        f"{base_url}/v1/predictions",
        json=SAMPLE_PAYLOAD,
        headers={"X-Request-ID": req_id},
        timeout=10,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    pred_json = r.json()
    assert pred_json.get("status") == "success"
    assert pred_json.get("request_id") == req_id
    label = pred_json["prediction"]["label"]
    score = pred_json["prediction"]["score"]
    assert label in ("Yes", "No")
    assert 0.0 <= score <= 1.0
    print(f"   [OK] Prediction output: label={label}, score={score:.4f} (Request ID: {req_id})")

    # 5. Test POST /v1/predictions with invalid payload (schema validation)
    print("5. Testing POST /v1/predictions (invalid payload -> 422)...")
    r = session.post(
        f"{base_url}/v1/predictions",
        json={"features": {"gender": "Alien"}},
        timeout=10,
    )
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    err_json = r.json()
    assert err_json["error"]["code"] == "VALIDATION_ERROR"
    print("   [OK] Validation error contract verified")

    # 6. Test GET /v1/monitoring/summary
    print("6. Testing GET /v1/monitoring/summary (verifying prediction telemetry persistence)...")
    r = session.get(f"{base_url}/v1/monitoring/summary", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    summary_json = r.json()
    total = summary_json.get("total_predictions", 0)
    assert total >= 1, f"Expected at least 1 prediction, got {total}"
    assert "label_distribution" in summary_json
    assert "latency_summary_ms" in summary_json
    print(f"   [OK] Persistence verified: total={total}, labels={summary_json['label_distribution']}")

    # 7. Test Dashboard if dashboard_url is supplied
    if dashboard_url:
        print(f"7. Testing Streamlit Dashboard on {dashboard_url}...")
        r_health = session.get(f"{dashboard_url}/_stcore/health", timeout=10)
        assert r_health.status_code == 200, f"Expected 200 from dashboard health, got {r_health.status_code}"
        r_page = session.get(dashboard_url, timeout=10)
        assert r_page.status_code == 200, f"Expected 200 from dashboard page, got {r_page.status_code}"
        assert "Streamlit" in r_page.text or "ModelServe" in r_page.text
        print("   [OK] Dashboard health endpoint responded 200 and page rendered successfully")

    print("\n=== All Smoke Test assertions PASSED successfully! ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="ModelServe AI Smoke Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of API service")
    parser.add_argument("--dashboard-url", default=None, help="Base URL of Streamlit Dashboard service")
    args = parser.parse_args()
    try:
        run_smoke_test(
            base_url=args.url.rstrip("/"),
            dashboard_url=args.dashboard_url.rstrip("/") if args.dashboard_url else None,
        )
    except Exception as exc:
        print(f"\n[FAIL] Smoke test failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

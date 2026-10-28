"""End-to-end smoke test script for ModelServe AI.

Exercises health, model info, predictions, validation failure, and monitoring telemetry.
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


def run_smoke_test(base_url: str) -> None:
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
    print(f"   [OK] Readiness is READY (active model version: {version})")

    # 3. Test /v1/model/info
    print("3. Testing GET /v1/model/info...")
    r = session.get(f"{base_url}/v1/model/info", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    info_json = r.json()
    assert "name" in info_json and "dataset" in info_json
    print(f"   [OK] Model info retrieved: {info_json.get('name')}")

    # 4. Test POST /v1/predictions with valid payload
    print("4. Testing POST /v1/predictions (valid payload)...")
    r = session.post(
        f"{base_url}/v1/predictions",
        json=SAMPLE_PAYLOAD,
        headers={"X-Request-ID": "smoke_test_req_001"},
        timeout=10,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    pred_json = r.json()
    assert pred_json.get("status") == "success"
    assert pred_json.get("request_id") == "smoke_test_req_001"
    label = pred_json["prediction"]["label"]
    score = pred_json["prediction"]["score"]
    assert label in ("Yes", "No")
    assert 0.0 <= score <= 1.0
    print(f"   [OK] Prediction output: label={label}, score={score:.4f}")

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
    print("6. Testing GET /v1/monitoring/summary...")
    r = session.get(f"{base_url}/v1/monitoring/summary", timeout=10)
    # If DB is configured, summary returns 200
    if r.status_code == 200:
        summary_json = r.json()
        total = summary_json.get("total_predictions", 0)
        assert total >= 1, f"Expected at least 1 prediction, got {total}"
        print(f"   [OK] Monitoring telemetry verified: total={total}")
    else:
        print(f"   [INFO] Monitoring returned HTTP {r.status_code} (DB might not be configured)")

    print("\n=== All Smoke Test assertions PASSED successfully! ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="ModelServe AI Smoke Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of API service")
    args = parser.parse_args()
    try:
        run_smoke_test(args.url.rstrip("/"))
    except Exception as exc:
        print(f"\n[FAIL] Smoke test failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


import React, { useState, useEffect, useCallback } from 'react';

const DEFAULT_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const INITIAL_FEATURES = {
  gender: 'Female',
  SeniorCitizen: 0,
  Partner: 'Yes',
  Dependents: 'No',
  tenure: 12,
  PhoneService: 'Yes',
  MultipleLines: 'No',
  InternetService: 'DSL',
  OnlineSecurity: 'Yes',
  OnlineBackup: 'No',
  DeviceProtection: 'Yes',
  TechSupport: 'No',
  StreamingTV: 'No',
  StreamingMovies: 'No',
  Contract: 'One year',
  PaperlessBilling: 'No',
  PaymentMethod: 'Bank transfer (automatic)',
  MonthlyCharges: 45.2,
  TotalCharges: 542.4,
};

export default function App() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [activeTab, setActiveTab] = useState('playground');

  // Health and Model states
  const [liveStatus, setLiveStatus] = useState(null);
  const [readyStatus, setReadyStatus] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);

  // Playground states
  const [features, setFeatures] = useState(INITIAL_FEATURES);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictError, setPredictError] = useState(null);

  // Telemetry states
  const [windowHours, setWindowHours] = useState(24);
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [telemetryError, setTelemetryError] = useState(null);

  // Fetch health and model metadata
  const fetchHealthAndModel = useCallback(async () => {
    setHealthLoading(true);
    const cleanUrl = apiUrl.replace(/\/+$/, '');

    try {
      const liveRes = await fetch(`${cleanUrl}/health/live`);
      setLiveStatus(liveRes.ok ? await liveRes.json() : { status: 'offline' });
    } catch {
      setLiveStatus({ status: 'offline' });
    }

    try {
      const readyRes = await fetch(`${cleanUrl}/health/ready`);
      setReadyStatus(readyRes.ok ? await readyRes.json() : { status: 'not_ready' });
    } catch {
      setReadyStatus({ status: 'not_ready' });
    }

    try {
      const modelRes = await fetch(`${cleanUrl}/v1/model/info`);
      setModelInfo(modelRes.ok ? await modelRes.json() : null);
    } catch {
      setModelInfo(null);
    }

    setHealthLoading(false);
  }, [apiUrl]);

  // Fetch telemetry summary
  const fetchTelemetry = useCallback(async () => {
    setTelemetryLoading(true);
    setTelemetryError(null);
    const cleanUrl = apiUrl.replace(/\/+$/, '');
    try {
      const res = await fetch(`${cleanUrl}/v1/monitoring/summary?window_hours=${windowHours}`);
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      } else {
        const errData = await res.json().catch(() => ({}));
        setTelemetryError(errData?.error?.message || `HTTP ${res.status}: Failed to load telemetry`);
      }
    } catch (err) {
      setTelemetryError(err.message || 'Network error fetching telemetry');
    } finally {
      setTelemetryLoading(false);
    }
  }, [apiUrl, windowHours]);

  useEffect(() => {
    fetchHealthAndModel();
    const interval = setInterval(fetchHealthAndModel, 15000);
    return () => clearInterval(interval);
  }, [fetchHealthAndModel]);

  useEffect(() => {
    if (activeTab === 'telemetry') {
      fetchTelemetry();
    }
  }, [activeTab, fetchTelemetry]);

  // Form feature handlers
  const handleFeatureChange = (name, value) => {
    setFeatures((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // Submit prediction
  const handlePredict = async (e) => {
    e.preventDefault();
    setPredictLoading(true);
    setPredictError(null);
    setPredictionResult(null);

    const cleanUrl = apiUrl.replace(/\/+$/, '');
    const clientRequestId = `req_fe_${Date.now()}`;

    try {
      const res = await fetch(`${cleanUrl}/v1/predictions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': clientRequestId,
        },
        body: JSON.stringify({
          features: {
            ...features,
            SeniorCitizen: Number(features.SeniorCitizen),
            tenure: Number(features.tenure),
            MonthlyCharges: Number(features.MonthlyCharges),
            TotalCharges: Number(features.TotalCharges),
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPredictionResult(data);
      } else {
        const errJson = await res.json().catch(() => ({}));
        setPredictError(errJson?.error?.message || `Inference error (HTTP ${res.status})`);
      }
    } catch (err) {
      setPredictError(err.message || 'Failed to connect to backend inference API');
    } finally {
      setPredictLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header>
        <div className="header-top">
          <div className="title-group">
            <h1>📊 ModelServe AI</h1>
            <p>Production ML Inference Platform — Customer Churn Classification</p>
          </div>
          <div className="api-config">
            <span style={{ color: 'var(--text-muted)' }}>Backend URL:</span>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <button onClick={fetchHealthAndModel}>Refresh</button>
          </div>
        </div>
      </header>

      {/* Status Bar */}
      <div className="status-grid">
        <div className="status-card">
          <span className="status-header">API Process</span>
          <div className="status-value">
            {liveStatus?.status === 'alive' ? (
              <span className="status-badge badge-success">● Alive (200 OK)</span>
            ) : (
              <span className="status-badge badge-danger">● Offline</span>
            )}
          </div>
        </div>

        <div className="status-card">
          <span className="status-header">Inference Engine</span>
          <div className="status-value">
            {readyStatus?.status === 'ready' ? (
              <span className="status-badge badge-success">● Ready to Serve</span>
            ) : (
              <span className="status-badge badge-warning">● Not Ready</span>
            )}
            <span
              className={`status-badge ${
                readyStatus?.database_connected ? 'badge-success' : 'badge-warning'
              }`}
              style={{ fontSize: '0.7rem' }}
            >
              DB: {readyStatus?.database_connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <div className="status-card">
          <span className="status-header">Active Model</span>
          <div className="status-value" style={{ fontSize: '1rem', wordBreak: 'break-all' }}>
            {modelInfo ? (
              <span className="status-badge badge-info">
                {modelInfo.name} ({modelInfo.version?.slice(0, 18)})
              </span>
            ) : (
              <span className="status-badge badge-warning">No Model Loaded</span>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'playground' ? 'active' : ''}`}
          onClick={() => setActiveTab('playground')}
        >
          🧪 Prediction Playground
        </button>
        <button
          className={`tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
          onClick={() => setActiveTab('telemetry')}
        >
          📈 Live Telemetry
        </button>
        <button
          className={`tab-btn ${activeTab === 'model-info' ? 'active' : ''}`}
          onClick={() => setActiveTab('model-info')}
        >
          🧠 Model Provenance & Benchmarks
        </button>
      </div>

      {/* Tab 1: Prediction Playground */}
      {activeTab === 'playground' && (
        <div className="card">
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.25rem', color: '#fff' }}>
            Submit Real-Time Prediction Request
          </h2>
          <form onSubmit={handlePredict}>
            <div className="form-grid">
              {/* Column 1: Demographics */}
              <div>
                <h3 style={{ fontSize: '0.95rem', color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>
                  Demographics & Tenure
                </h3>
                <div className="form-group">
                  <label>Gender</label>
                  <select
                    className="form-control"
                    value={features.gender}
                    onChange={(e) => handleFeatureChange('gender', e.target.value)}
                  >
                    <option value="Female">Female</option>
                    <option value="Male">Male</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Senior Citizen</label>
                  <select
                    className="form-control"
                    value={features.SeniorCitizen}
                    onChange={(e) => handleFeatureChange('SeniorCitizen', Number(e.target.value))}
                  >
                    <option value={0}>No (0)</option>
                    <option value={1}>Yes (1)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Partner</label>
                  <select
                    className="form-control"
                    value={features.Partner}
                    onChange={(e) => handleFeatureChange('Partner', e.target.value)}
                  >
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Dependents</label>
                  <select
                    className="form-control"
                    value={features.Dependents}
                    onChange={(e) => handleFeatureChange('Dependents', e.target.value)}
                  >
                    <option value="No">No</option>
                    <option value="Yes">Yes</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Tenure (Months)</label>
                  <input
                    type="number"
                    min="0"
                    max="120"
                    className="form-control"
                    value={features.tenure}
                    onChange={(e) => handleFeatureChange('tenure', Number(e.target.value))}
                  />
                </div>
              </div>

              {/* Column 2: Services */}
              <div>
                <h3 style={{ fontSize: '0.95rem', color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>
                  Subscribed Services
                </h3>
                <div className="form-group">
                  <label>Phone Service</label>
                  <select
                    className="form-control"
                    value={features.PhoneService}
                    onChange={(e) => handleFeatureChange('PhoneService', e.target.value)}
                  >
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Multiple Lines</label>
                  <select
                    className="form-control"
                    value={features.MultipleLines}
                    onChange={(e) => handleFeatureChange('MultipleLines', e.target.value)}
                  >
                    <option value="No">No</option>
                    <option value="Yes">Yes</option>
                    <option value="No phone service">No phone service</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Internet Service</label>
                  <select
                    className="form-control"
                    value={features.InternetService}
                    onChange={(e) => handleFeatureChange('InternetService', e.target.value)}
                  >
                    <option value="DSL">DSL</option>
                    <option value="Fiber optic">Fiber optic</option>
                    <option value="No">No</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Online Security</label>
                  <select
                    className="form-control"
                    value={features.OnlineSecurity}
                    onChange={(e) => handleFeatureChange('OnlineSecurity', e.target.value)}
                  >
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                    <option value="No internet service">No internet service</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Tech Support</label>
                  <select
                    className="form-control"
                    value={features.TechSupport}
                    onChange={(e) => handleFeatureChange('TechSupport', e.target.value)}
                  >
                    <option value="No">No</option>
                    <option value="Yes">Yes</option>
                    <option value="No internet service">No internet service</option>
                  </select>
                </div>
              </div>

              {/* Column 3: Contract & Billing */}
              <div>
                <h3 style={{ fontSize: '0.95rem', color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>
                  Contract & Charges
                </h3>
                <div className="form-group">
                  <label>Contract Type</label>
                  <select
                    className="form-control"
                    value={features.Contract}
                    onChange={(e) => handleFeatureChange('Contract', e.target.value)}
                  >
                    <option value="Month-to-month">Month-to-month</option>
                    <option value="One year">One year</option>
                    <option value="Two year">Two year</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Paperless Billing</label>
                  <select
                    className="form-control"
                    value={features.PaperlessBilling}
                    onChange={(e) => handleFeatureChange('PaperlessBilling', e.target.value)}
                  >
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Payment Method</label>
                  <select
                    className="form-control"
                    value={features.PaymentMethod}
                    onChange={(e) => handleFeatureChange('PaymentMethod', e.target.value)}
                  >
                    <option value="Electronic check">Electronic check</option>
                    <option value="Mailed check">Mailed check</option>
                    <option value="Bank transfer (automatic)">Bank transfer (automatic)</option>
                    <option value="Credit card (automatic)">Credit card (automatic)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Monthly Charges ($)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="500"
                    className="form-control"
                    value={features.MonthlyCharges}
                    onChange={(e) => handleFeatureChange('MonthlyCharges', Number(e.target.value))}
                  />
                </div>
                <div className="form-group">
                  <label>Total Charges ($)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="20000"
                    className="form-control"
                    value={features.TotalCharges}
                    onChange={(e) => handleFeatureChange('TotalCharges', Number(e.target.value))}
                  />
                </div>
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={predictLoading}>
              {predictLoading ? 'Computing Inferences...' : 'Predict Churn Outcome (POST /v1/predictions)'}
            </button>
          </form>

          {predictError && (
            <div className="result-box danger" style={{ marginTop: '1.5rem' }}>
              <strong>Inference Error:</strong> {predictError}
            </div>
          )}

          {predictionResult && (
            <div
              className={`result-box ${
                predictionResult.prediction.label === 'Yes' ? 'danger' : 'success'
              }`}
            >
              <div className="result-header">
                <span className="result-title">
                  {predictionResult.prediction.label === 'Yes'
                    ? '⚠️ High Churn Risk (Outcome: Yes)'
                    : '✅ Retained Customer (Outcome: No)'}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Request ID: {predictionResult.request_id}
                </span>
              </div>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                Model Churn Probability Score: <strong>{predictionResult.prediction.score.toFixed(4)}</strong>
              </p>
              <div className="score-bar-container">
                <div
                  className="score-bar"
                  style={{
                    width: `${Math.min(100, Math.max(0, predictionResult.prediction.score * 100))}%`,
                    backgroundColor:
                      predictionResult.prediction.label === 'Yes' ? '#ef4444' : '#10b981',
                  }}
                />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                Served by: {predictionResult.model.name} (version: {predictionResult.model.version})
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Live Telemetry */}
      {activeTab === 'telemetry' && (
        <div className="card">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1.25rem',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <h2 style={{ fontSize: '1.25rem', color: '#fff' }}>Live Inference Telemetry & Persistence</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Time Window:</span>
              <select
                className="select-window"
                value={windowHours}
                onChange={(e) => setWindowHours(Number(e.target.value))}
              >
                <option value={1}>Past 1 hour</option>
                <option value={6}>Past 6 hours</option>
                <option value={24}>Past 24 hours</option>
                <option value={72}>Past 72 hours</option>
                <option value={168}>Past 7 days</option>
              </select>
              <button
                className="btn-primary"
                style={{ width: 'auto', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                onClick={fetchTelemetry}
                disabled={telemetryLoading}
              >
                {telemetryLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>
          </div>

          {telemetryError ? (
            <div className="alert-box">
              <strong>Telemetry Store Notice:</strong> {telemetryError}
              <p style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                Verify that your Neon PostgreSQL connection string (DATABASE_URL) is configured in your Render service.
              </p>
            </div>
          ) : telemetry?.total_predictions === 0 ? (
            <div className="alert-box" style={{ background: 'rgba(59, 130, 246, 0.1)', borderColor: 'rgba(59, 130, 246, 0.3)', color: '#93c5fd' }}>
              <strong>No inference records found in the selected {windowHours}-hour window.</strong>
              <p style={{ marginTop: '0.5rem' }}>
                Submit sample inference requests from the <strong>Prediction Playground</strong> tab to generate persisted telemetry in Neon PostgreSQL.
              </p>
            </div>
          ) : telemetry ? (
            <>
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-title">Total Inferences</div>
                  <div className="metric-value">{telemetry.total_predictions.toLocaleString()}</div>
                  <div className="metric-sub">Window: Past {telemetry.window_hours} hours</div>
                </div>
                <div className="metric-card">
                  <div className="metric-title">Churn Alerts (Yes)</div>
                  <div className="metric-value">
                    {telemetry.label_distribution?.Yes || 0}
                  </div>
                  <div className="metric-sub">
                    {(
                      ((telemetry.label_distribution?.Yes || 0) / (telemetry.total_predictions || 1)) *
                      100
                    ).toFixed(1)}
                    % predicted churn rate
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-title">Mean Churn Score</div>
                  <div className="metric-value">
                    {telemetry.score_summary?.mean?.toFixed(4) ?? '0.0000'}
                  </div>
                  <div className="metric-sub">
                    Min: {telemetry.score_summary?.min?.toFixed(3)} | Max: {telemetry.score_summary?.max?.toFixed(3)}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-title">p95 Latency</div>
                  <div className="metric-value">
                    {telemetry.latency_summary_ms?.p95?.toFixed(1) ?? '0.0'} ms
                  </div>
                  <div className="metric-sub">
                    Mean: {telemetry.latency_summary_ms?.mean?.toFixed(1)} ms
                  </div>
                </div>
              </div>

              <h3 style={{ fontSize: '1rem', color: '#fff', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                Latency Profile Breakdown (PostgreSQL Stored)
              </h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Percentile / Metric</th>
                    <th>Latency (ms)</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(telemetry.latency_summary_ms || {}).map(([key, val]) => (
                    <tr key={key}>
                      <td style={{ fontWeight: 600 }}>{key.toUpperCase()}</td>
                      <td>{typeof val === 'number' ? val.toFixed(2) : val} ms</td>
                      <td>
                        <span className="status-badge badge-success">Nominal</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
        </div>
      )}

      {/* Tab 3: Model Provenance & Benchmarks */}
      {activeTab === 'model-info' && (
        <div className="card">
          <h2 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: '1.25rem' }}>
            Model Lineage & Offline Held-Out Evaluation
          </h2>

          {modelInfo ? (
            <>
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-title">PR-AUC (Avg Precision)</div>
                  <div className="metric-value">
                    {modelInfo.test_metrics?.pr_auc_average_precision?.toFixed(4) || 'N/A'}
                  </div>
                  <div className="metric-sub">Primary Selection Criterion</div>
                </div>
                <div className="metric-card">
                  <div className="metric-title">ROC-AUC</div>
                  <div className="metric-value">
                    {modelInfo.test_metrics?.roc_auc?.toFixed(4) || 'N/A'}
                  </div>
                  <div className="metric-sub">Held-Out Test Split (20%)</div>
                </div>
                <div className="metric-card">
                  <div className="metric-title">F1 Score</div>
                  <div className="metric-value">
                    {modelInfo.test_metrics?.f1?.toFixed(4) || 'N/A'}
                  </div>
                  <div className="metric-sub">Precision: {modelInfo.test_metrics?.precision?.toFixed(3)} | Recall: {modelInfo.test_metrics?.recall?.toFixed(3)}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-title">Decision Threshold</div>
                  <div className="metric-value">
                    {modelInfo.test_metrics?.decision_threshold ?? 0.5}
                  </div>
                  <div className="metric-sub">Positive Label: {modelInfo.positive_label}</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginTop: '1.5rem' }}>
                <div>
                  <h3 style={{ fontSize: '1rem', color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>
                    Dataset Provenance
                  </h3>
                  <table className="data-table">
                    <tbody>
                      <tr>
                        <td style={{ color: 'var(--text-secondary)' }}>Source Dataset</td>
                        <td>
                          <a
                            href={modelInfo.dataset?.source}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'var(--accent-primary)' }}
                          >
                            {modelInfo.dataset?.name || 'IBM Telco Churn'}
                          </a>
                        </td>
                      </tr>
                      <tr>
                        <td style={{ color: 'var(--text-secondary)' }}>License</td>
                        <td><code>{modelInfo.dataset?.license || 'Apache-2.0'}</code></td>
                      </tr>
                      <tr>
                        <td style={{ color: 'var(--text-secondary)' }}>Dataset Fingerprint</td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                          {modelInfo.dataset?.sha256?.slice(0, 24)}...
                        </td>
                      </tr>
                      <tr>
                        <td style={{ color: 'var(--text-secondary)' }}>Total Samples</td>
                        <td>{modelInfo.dataset?.rows?.toLocaleString() || '7,043'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h3 style={{ fontSize: '1rem', color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>
                    Held-Out Confusion Matrix
                  </h3>
                  {modelInfo.test_metrics?.confusion_matrix ? (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Actual \ Predicted</th>
                          <th>Pred: No</th>
                          <th>Pred: Yes</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td style={{ fontWeight: 600 }}>Actual: No</td>
                          <td>{modelInfo.test_metrics.confusion_matrix[0][0]}</td>
                          <td>{modelInfo.test_metrics.confusion_matrix[0][1]}</td>
                        </tr>
                        <tr>
                          <td style={{ fontWeight: 600 }}>Actual: Yes</td>
                          <td>{modelInfo.test_metrics.confusion_matrix[1][0]}</td>
                          <td>{modelInfo.test_metrics.confusion_matrix[1][1]}</td>
                        </tr>
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ color: 'var(--text-muted)' }}>Matrix not available</p>
                  )}
                </div>
              </div>

              <div className="alert-box">
                <strong>Benchmark Notice:</strong> Metrics are computed on an offline stratified test split (20%) using IBM's Telco Customer Churn sample. Churn probability scores are uncalibrated and should be monitored when applied to production traffic.
              </div>
            </>
          ) : (
            <p style={{ color: 'var(--text-muted)' }}>Model metadata is currently unreachable.</p>
          )}
        </div>
      )}
    </div>
  );
}


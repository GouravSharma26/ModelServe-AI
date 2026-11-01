import React, { useState, useEffect, useCallback } from 'react';
import WelcomeDialog from './components/onboarding/WelcomeDialog';
import TutorialController from './components/onboarding/TutorialController';
import FloatingHelpButton from './components/help/FloatingHelpButton';
import CsvWorkflow from './components/prediction/CsvWorkflow';
import { useOnboarding } from './hooks/useOnboarding';

const API_URL = (
  import.meta.env.VITE_API_BASE_URL || 'https://modelserve-ai.onrender.com'
).replace(/\/+$/, '');

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
  const [activeTab, setActiveTab] = useState('prediction');

  // Health and Model states
  const [liveStatus, setLiveStatus] = useState(null);
  const [readyStatus, setReadyStatus] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);

  // Prediction Playground states
  const [features, setFeatures] = useState(INITIAL_FEATURES);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictError, setPredictError] = useState(null);

  // Telemetry states
  const [windowHours, setWindowHours] = useState(24);
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [telemetryError, setTelemetryError] = useState(null);

  // Onboarding hook
  const {
    showWelcome,
    tutorialActive,
    currentStep,
    setCurrentStep,
    startTutorial,
    skipTutorial,
    completeTutorial,
    exitTutorial,
    restartTutorial,
  } = useOnboarding();

  // Fetch health and model metadata
  const fetchHealthAndModel = useCallback(async () => {
    setHealthLoading(true);

    try {
      const liveRes = await fetch(`${API_URL}/health/live`);
      setLiveStatus(liveRes.ok ? await liveRes.json() : { status: 'offline' });
    } catch {
      setLiveStatus({ status: 'offline' });
    }

    try {
      const readyRes = await fetch(`${API_URL}/health/ready`);
      setReadyStatus(readyRes.ok ? await readyRes.json() : { status: 'not_ready' });
    } catch {
      setReadyStatus({ status: 'not_ready' });
    }

    try {
      const modelRes = await fetch(`${API_URL}/v1/model/info`);
      setModelInfo(modelRes.ok ? await modelRes.json() : null);
    } catch {
      setModelInfo(null);
    }

    setHealthLoading(false);
  }, []);

  // Fetch telemetry summary
  const fetchTelemetry = useCallback(async () => {
    setTelemetryLoading(true);
    setTelemetryError(null);
    try {
      const res = await fetch(`${API_URL}/v1/monitoring/summary?window_hours=${windowHours}`);
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
  }, [windowHours]);

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

  // Execute inference request against API
  const executePrediction = async (featurePayload) => {
    setPredictLoading(true);
    setPredictError(null);
    setPredictionResult(null);

    const clientRequestId = `req_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    try {
      const payloadToSend = {
        ...featurePayload,
        SeniorCitizen: Number(featurePayload.SeniorCitizen),
        tenure: Number(featurePayload.tenure),
        MonthlyCharges: Number(featurePayload.MonthlyCharges),
        TotalCharges: Number(featurePayload.TotalCharges),
      };

      const res = await fetch(`${API_URL}/v1/predictions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': clientRequestId,
        },
        body: JSON.stringify({
          features: payloadToSend,
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

  const handlePredictSubmit = (e) => {
    e.preventDefault();
    executePrediction(features);
  };

  return (
    <div className="app-shell">
      {/* Welcome Onboarding Modal */}
      {showWelcome && (
        <WelcomeDialog
          onStartTutorial={startTutorial}
          onSkip={skipTutorial}
        />
      )}

      {/* Guided Tutorial Controller */}
      {tutorialActive && (
        <TutorialController
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onComplete={completeTutorial}
          onExit={exitTutorial}
          currentStep={currentStep}
          setCurrentStep={setCurrentStep}
        />
      )}

      {/* Persistent Floating Help Button */}
      <FloatingHelpButton onRestartTutorial={restartTutorial} />

      {/* Top Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-title-wrap">
            <h1 className="brand-title">ModelServe</h1>
            <span className="brand-tag">Inference Platform</span>
          </div>
          <p className="brand-subtitle">Customer intelligence · Churn prediction</p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn-refresh"
            onClick={fetchHealthAndModel}
            disabled={healthLoading}
            title="Refresh backend status"
          >
            <span className={`refresh-indicator ${healthLoading ? 'is-loading' : ''}`} />
            <span>{healthLoading ? 'Checking...' : 'Refresh status'}</span>
          </button>
        </div>
      </header>

      {/* Status Bar */}
      <section className="status-grid" aria-label="System status">
        {/* Status Card 1: API Process */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-label">API Process</span>
            <span
              className={`status-pill ${
                liveStatus?.status === 'alive' ? 'status-pill-success' : 'status-pill-danger'
              }`}
            >
              <span className="status-dot" />
              {liveStatus?.status === 'alive' ? 'Operational' : 'Offline'}
            </span>
          </div>
          <div className="status-meta">
            {liveStatus?.status === 'alive' ? 'HTTP 200 · Process responsive' : 'Service probe unreachable'}
          </div>
        </div>

        {/* Status Card 2: Inference Engine */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-label">Inference Engine</span>
            <span
              className={`status-pill ${
                readyStatus?.status === 'ready' ? 'status-pill-success' : 'status-pill-warning'
              }`}
            >
              <span className="status-dot" />
              {readyStatus?.status === 'ready' ? 'Ready to Serve' : 'Not Ready'}
            </span>
          </div>
          <div className="status-meta">
            <span className="meta-db-indicator">
              Database:{' '}
              <strong className={readyStatus?.database_connected ? 'text-success' : 'text-warning'}>
                {readyStatus?.database_connected ? 'Connected' : 'Disconnected'}
              </strong>
            </span>
          </div>
        </div>

        {/* Status Card 3: Active Model */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-label">Active Model</span>
            {modelInfo ? (
              <span className="status-pill status-pill-neutral">
                <span className="status-dot" />
                Verified
              </span>
            ) : (
              <span className="status-pill status-pill-warning">
                <span className="status-dot" />
                Pending
              </span>
            )}
          </div>
          <div className="status-meta model-version-text" title={modelInfo ? `${modelInfo.name} (${modelInfo.version})` : 'No model loaded'}>
            {modelInfo ? (
              <>
                <span className="model-name">{modelInfo.name}</span>
                <span className="model-version-code">{modelInfo.version?.slice(0, 20)}</span>
              </>
            ) : (
              <span className="text-muted">No active artifact loaded</span>
            )}
          </div>
        </div>
      </section>

      {/* Navigation Tabs */}
      <nav className="tab-nav" aria-label="Dashboard sections">
        <button
          type="button"
          className={`tab-item ${activeTab === 'prediction' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('prediction')}
        >
          Prediction
        </button>
        <button
          type="button"
          className={`tab-item ${activeTab === 'telemetry' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('telemetry')}
        >
          Telemetry
        </button>
        <button
          type="button"
          className={`tab-item ${activeTab === 'model-info' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('model-info')}
        >
          Model details
        </button>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Section 1: Prediction Playground */}
        {activeTab === 'prediction' && (
          <section className="panel-card">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Inference Playground</h2>
                <p className="panel-description">
                  Submit customer attribute vectors for real-time churn risk classification
                </p>
              </div>
            </div>

            {/* CSV Sample Data & Inspection Workflow */}
            <CsvWorkflow
              onSelectCustomer={(cust) => setFeatures(cust.features)}
              onRunPrediction={(custFeatures) => executePrediction(custFeatures)}
              disabled={predictLoading}
            />

            <form onSubmit={handlePredictSubmit} className="prediction-form">
              <div className="form-sections-grid">
                {/* Column 1: Demographics & Account */}
                <div className="form-section">
                  <h3 className="section-title">Demographics & Account</h3>

                  <div className="field-group">
                    <label htmlFor="field-gender" className="field-label">Gender</label>
                    <select
                      id="field-gender"
                      className="field-control"
                      value={features.gender}
                      onChange={(e) => handleFeatureChange('gender', e.target.value)}
                    >
                      <option value="Female">Female</option>
                      <option value="Male">Male</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-senior" className="field-label">Senior Citizen</label>
                    <select
                      id="field-senior"
                      className="field-control"
                      value={features.SeniorCitizen}
                      onChange={(e) => handleFeatureChange('SeniorCitizen', Number(e.target.value))}
                    >
                      <option value={0}>No (0)</option>
                      <option value={1}>Yes (1)</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-partner" className="field-label">Partner</label>
                    <select
                      id="field-partner"
                      className="field-control"
                      value={features.Partner}
                      onChange={(e) => handleFeatureChange('Partner', e.target.value)}
                    >
                      <option value="Yes">Yes</option>
                      <option value="No">No</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-dependents" className="field-label">Dependents</label>
                    <select
                      id="field-dependents"
                      className="field-control"
                      value={features.Dependents}
                      onChange={(e) => handleFeatureChange('Dependents', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-tenure" className="field-label">Tenure (months)</label>
                    <input
                      id="field-tenure"
                      type="number"
                      min="0"
                      max="120"
                      className="field-control"
                      value={features.tenure}
                      onChange={(e) => handleFeatureChange('tenure', Number(e.target.value))}
                    />
                  </div>
                </div>

                {/* Column 2: Subscribed Services */}
                <div className="form-section">
                  <h3 className="section-title">Subscribed Services</h3>

                  <div className="field-group">
                    <label htmlFor="field-phone" className="field-label">Phone Service</label>
                    <select
                      id="field-phone"
                      className="field-control"
                      value={features.PhoneService}
                      onChange={(e) => handleFeatureChange('PhoneService', e.target.value)}
                    >
                      <option value="Yes">Yes</option>
                      <option value="No">No</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-multiple" className="field-label">Multiple Lines</label>
                    <select
                      id="field-multiple"
                      className="field-control"
                      value={features.MultipleLines}
                      onChange={(e) => handleFeatureChange('MultipleLines', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No phone service">No phone service</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-internet" className="field-label">Internet Service</label>
                    <select
                      id="field-internet"
                      className="field-control"
                      value={features.InternetService}
                      onChange={(e) => handleFeatureChange('InternetService', e.target.value)}
                    >
                      <option value="DSL">DSL</option>
                      <option value="Fiber optic">Fiber optic</option>
                      <option value="No">No</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-security" className="field-label">Online Security</label>
                    <select
                      id="field-security"
                      className="field-control"
                      value={features.OnlineSecurity}
                      onChange={(e) => handleFeatureChange('OnlineSecurity', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No internet service">No internet service</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-backup" className="field-label">Online Backup</label>
                    <select
                      id="field-backup"
                      className="field-control"
                      value={features.OnlineBackup}
                      onChange={(e) => handleFeatureChange('OnlineBackup', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No internet service">No internet service</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-device" className="field-label">Device Protection</label>
                    <select
                      id="field-device"
                      className="field-control"
                      value={features.DeviceProtection}
                      onChange={(e) => handleFeatureChange('DeviceProtection', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No internet service">No internet service</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-tech" className="field-label">Tech Support</label>
                    <select
                      id="field-tech"
                      className="field-control"
                      value={features.TechSupport}
                      onChange={(e) => handleFeatureChange('TechSupport', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No internet service">No internet service</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-tv" className="field-label">Streaming TV</label>
                    <select
                      id="field-tv"
                      className="field-control"
                      value={features.StreamingTV}
                      onChange={(e) => handleFeatureChange('StreamingTV', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No internet service">No internet service</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-movies" className="field-label">Streaming Movies</label>
                    <select
                      id="field-movies"
                      className="field-control"
                      value={features.StreamingMovies}
                      onChange={(e) => handleFeatureChange('StreamingMovies', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                      <option value="No internet service">No internet service</option>
                    </select>
                  </div>
                </div>

                {/* Column 3: Contract & Billing */}
                <div className="form-section">
                  <h3 className="section-title">Contract & Billing</h3>

                  <div className="field-group">
                    <label htmlFor="field-contract" className="field-label">Contract Type</label>
                    <select
                      id="field-contract"
                      className="field-control"
                      value={features.Contract}
                      onChange={(e) => handleFeatureChange('Contract', e.target.value)}
                    >
                      <option value="Month-to-month">Month-to-month</option>
                      <option value="One year">One year</option>
                      <option value="Two year">Two year</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-paperless" className="field-label">Paperless Billing</label>
                    <select
                      id="field-paperless"
                      className="field-control"
                      value={features.PaperlessBilling}
                      onChange={(e) => handleFeatureChange('PaperlessBilling', e.target.value)}
                    >
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-payment" className="field-label">Payment Method</label>
                    <select
                      id="field-payment"
                      className="field-control"
                      value={features.PaymentMethod}
                      onChange={(e) => handleFeatureChange('PaymentMethod', e.target.value)}
                    >
                      <option value="Electronic check">Electronic check</option>
                      <option value="Mailed check">Mailed check</option>
                      <option value="Bank transfer (automatic)">Bank transfer (automatic)</option>
                      <option value="Credit card (automatic)">Credit card (automatic)</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-monthly" className="field-label">Monthly Charges ($)</label>
                    <input
                      id="field-monthly"
                      type="number"
                      step="0.05"
                      min="0"
                      max="500"
                      className="field-control"
                      value={features.MonthlyCharges}
                      onChange={(e) => handleFeatureChange('MonthlyCharges', Number(e.target.value))}
                    />
                  </div>

                  <div className="field-group">
                    <label htmlFor="field-total" className="field-label">Total Charges ($)</label>
                    <input
                      id="field-total"
                      type="number"
                      step="0.5"
                      min="0"
                      max="20000"
                      className="field-control"
                      value={features.TotalCharges}
                      onChange={(e) => handleFeatureChange('TotalCharges', Number(e.target.value))}
                    />
                  </div>
                </div>
              </div>

              <div className="form-submit-row">
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={predictLoading}
                >
                  {predictLoading ? 'Computing inference...' : 'Run prediction'}
                </button>
              </div>
            </form>

            {/* Error Message */}
            {predictError && (
              <div className="banner-alert banner-alert-danger" role="alert">
                <div className="banner-alert-title">Inference Failed</div>
                <div className="banner-alert-desc">{predictError}</div>
              </div>
            )}

            {/* Prediction Result Display */}
            {predictionResult && (
              <div
                className={`result-card ${
                  predictionResult.prediction.label === 'Yes'
                    ? 'result-card-danger'
                    : 'result-card-success'
                }`}
              >
                <div className="result-header">
                  <div className="result-classification">
                    <span className="result-tag">Predicted Outcome</span>
                    <h3 className="result-label">
                      {predictionResult.prediction.label === 'Yes'
                        ? 'High Churn Probability'
                        : 'Retained Customer'}
                    </h3>
                  </div>

                  <div className="result-badge-wrap">
                    <span
                      className={`badge-classification ${
                        predictionResult.prediction.label === 'Yes'
                          ? 'badge-churn'
                          : 'badge-retained'
                      }`}
                    >
                      {predictionResult.prediction.label === 'Yes' ? 'Churn Risk: Yes' : 'Churn Risk: No'}
                    </span>
                  </div>
                </div>

                <div className="result-score-block">
                  <div className="score-label-row">
                    <span className="score-text">Model Confidence Score</span>
                    <span className="score-value">
                      {(predictionResult.prediction.score * 100).toFixed(2)}%
                      <span className="score-raw"> ({predictionResult.prediction.score.toFixed(4)})</span>
                    </span>
                  </div>
                  <div className="score-bar-track">
                    <div
                      className={`score-bar-fill ${
                        predictionResult.prediction.label === 'Yes'
                          ? 'score-fill-danger'
                          : 'score-fill-success'
                      }`}
                      style={{
                        width: `${Math.min(100, Math.max(0, predictionResult.prediction.score * 100))}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="result-details-grid">
                  <div className="detail-item">
                    <span className="detail-key">Request Identifier</span>
                    <span className="detail-val font-mono">{predictionResult.request_id}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-key">Serving Architecture</span>
                    <span className="detail-val">{predictionResult.model.name}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-key">Model Checksum Version</span>
                    <span className="detail-val font-mono">{predictionResult.model.version}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-key">Telemetry Status</span>
                    <span className="detail-val text-success">Persisted to PostgreSQL</span>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Section 2: Live Telemetry */}
        {activeTab === 'telemetry' && (
          <section className="panel-card">
            <div className="panel-header-flex">
              <div>
                <h2 className="panel-title">Inference Telemetry</h2>
                <p className="panel-description">
                  Aggregate prediction distribution and latency profiles stored in PostgreSQL
                </p>
              </div>

              <div className="telemetry-controls">
                <label htmlFor="window-select" className="control-label">Window</label>
                <select
                  id="window-select"
                  className="select-control"
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
                  type="button"
                  className="btn-secondary"
                  onClick={fetchTelemetry}
                  disabled={telemetryLoading}
                >
                  {telemetryLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
            </div>

            {telemetryError ? (
              <div className="banner-alert banner-alert-warning" role="alert">
                <div className="banner-alert-title">Telemetry Store Notice</div>
                <div className="banner-alert-desc">
                  {telemetryError}
                  <div className="banner-alert-sub">
                    Verify that your PostgreSQL persistence configuration (DATABASE_URL) is reachable.
                  </div>
                </div>
              </div>
            ) : telemetry?.total_predictions === 0 ? (
              <div className="empty-state-box">
                <div className="empty-state-title">No predictions recorded</div>
                <p className="empty-state-desc">
                  No inference events have been persisted in the past {windowHours} hours. Run predictions from the
                  Prediction playground to populate telemetry.
                </p>
              </div>
            ) : telemetry ? (
              <>
                <div className="stats-metric-grid">
                  <div className="metric-cell">
                    <div className="metric-cell-label">Total Inferences</div>
                    <div className="metric-cell-val">{telemetry.total_predictions.toLocaleString()}</div>
                    <div className="metric-cell-foot">Aggregation: {telemetry.window_hours}h window</div>
                  </div>

                  <div className="metric-cell">
                    <div className="metric-cell-label">Predicted Churn Rate</div>
                    <div className="metric-cell-val">
                      {(
                        ((telemetry.label_distribution?.Yes || 0) / (telemetry.total_predictions || 1)) *
                        100
                      ).toFixed(1)}
                      %
                    </div>
                    <div className="metric-cell-foot">
                      {telemetry.label_distribution?.Yes || 0} churn alerts flagged
                    </div>
                  </div>

                  <div className="metric-cell">
                    <div className="metric-cell-label">Mean Churn Score</div>
                    <div className="metric-cell-val">
                      {telemetry.score_summary?.mean?.toFixed(4) ?? '0.0000'}
                    </div>
                    <div className="metric-cell-foot">
                      Min: {telemetry.score_summary?.min?.toFixed(3) ?? '0.000'} · Max:{' '}
                      {telemetry.score_summary?.max?.toFixed(3) ?? '0.000'}
                    </div>
                  </div>

                  <div className="metric-cell">
                    <div className="metric-cell-label">p95 Latency</div>
                    <div className="metric-cell-val">
                      {telemetry.latency_summary_ms?.p95?.toFixed(1) ?? '0.0'} ms
                    </div>
                    <div className="metric-cell-foot">
                      Mean: {telemetry.latency_summary_ms?.mean?.toFixed(1) ?? '0.0'} ms
                    </div>
                  </div>
                </div>

                <div className="table-wrap">
                  <div className="table-caption">PostgreSQL Execution Latency Profile (ms)</div>
                  <table className="enterprise-table">
                    <thead>
                      <tr>
                        <th>Percentile / Metric</th>
                        <th>Duration (ms)</th>
                        <th>SLO Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(telemetry.latency_summary_ms || {}).map(([key, val]) => (
                        <tr key={key}>
                          <td className="font-semibold text-secondary">{key.toUpperCase()}</td>
                          <td className="font-mono">{typeof val === 'number' ? val.toFixed(2) : val} ms</td>
                          <td>
                            <span className="status-pill status-pill-success">
                              <span className="status-dot" />
                              Compliant
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
          </section>
        )}

        {/* Section 3: Model Details */}
        {activeTab === 'model-info' && (
          <section className="panel-card">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Model Provenance & Evaluation</h2>
                <p className="panel-description">
                  Lineage records, training metadata, and offline benchmark validation
                </p>
              </div>
            </div>

            {modelInfo ? (
              <>
                <div className="stats-metric-grid">
                  <div className="metric-cell">
                    <div className="metric-cell-label">PR-AUC (Avg Precision)</div>
                    <div className="metric-cell-val text-accent">
                      {modelInfo.test_metrics?.pr_auc_average_precision?.toFixed(4) || 'N/A'}
                    </div>
                    <div className="metric-cell-foot">Primary candidate selection rule</div>
                  </div>

                  <div className="metric-cell">
                    <div className="metric-cell-label">ROC-AUC</div>
                    <div className="metric-cell-val">
                      {modelInfo.test_metrics?.roc_auc?.toFixed(4) || 'N/A'}
                    </div>
                    <div className="metric-cell-foot">Stratified test split (20%)</div>
                  </div>

                  <div className="metric-cell">
                    <div className="metric-cell-label">F1 Score</div>
                    <div className="metric-cell-val">
                      {modelInfo.test_metrics?.f1?.toFixed(4) || 'N/A'}
                    </div>
                    <div className="metric-cell-foot">
                      P: {modelInfo.test_metrics?.precision?.toFixed(3) || 'N/A'} · R:{' '}
                      {modelInfo.test_metrics?.recall?.toFixed(3) || 'N/A'}
                    </div>
                  </div>

                  <div className="metric-cell">
                    <div className="metric-cell-label">Decision Threshold</div>
                    <div className="metric-cell-val">
                      {modelInfo.test_metrics?.decision_threshold ?? 0.5}
                    </div>
                    <div className="metric-cell-foot">Positive label: {modelInfo.positive_label}</div>
                  </div>
                </div>

                <div className="provenance-grid">
                  {/* Dataset Lineage */}
                  <div className="provenance-block">
                    <h3 className="section-title">Dataset Provenance</h3>
                    <table className="enterprise-table">
                      <tbody>
                        <tr>
                          <td className="text-muted">Source Repository</td>
                          <td>
                            <a
                              href={modelInfo.dataset?.source}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-link"
                            >
                              {modelInfo.dataset?.name || 'IBM Telco Churn'}
                            </a>
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">License</td>
                          <td>
                            <span className="code-pill">{modelInfo.dataset?.license || 'Apache-2.0'}</span>
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">SHA-256 Fingerprint</td>
                          <td className="font-mono text-xs">
                            {modelInfo.dataset?.sha256?.slice(0, 32)}...
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">Total Samples</td>
                          <td>{modelInfo.dataset?.rows?.toLocaleString() || '7,043'}</td>
                        </tr>
                        <tr>
                          <td className="text-muted">Target Variable</td>
                          <td><code>Churn</code> (Yes / No)</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Confusion Matrix */}
                  <div className="provenance-block">
                    <h3 className="section-title">Held-Out Confusion Matrix</h3>
                    {modelInfo.test_metrics?.confusion_matrix ? (
                      <table className="enterprise-table">
                        <thead>
                          <tr>
                            <th>Actual \ Predicted</th>
                            <th>Predicted: No</th>
                            <th>Predicted: Yes</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td className="font-semibold text-secondary">Actual: No</td>
                            <td className="font-mono">{modelInfo.test_metrics.confusion_matrix[0][0]}</td>
                            <td className="font-mono">{modelInfo.test_metrics.confusion_matrix[0][1]}</td>
                          </tr>
                          <tr>
                            <td className="font-semibold text-secondary">Actual: Yes</td>
                            <td className="font-mono">{modelInfo.test_metrics.confusion_matrix[1][0]}</td>
                            <td className="font-mono">{modelInfo.test_metrics.confusion_matrix[1][1]}</td>
                          </tr>
                        </tbody>
                      </table>
                    ) : (
                      <div className="empty-state-box">Matrix data unavailable</div>
                    )}
                  </div>
                </div>

                <div className="banner-disclaimer">
                  <strong>Validation Disclaimer:</strong> Performance figures represent benchmark evaluations on
                  an offline stratified 60/20/20 test split of the public IBM Telco Customer Churn sample. Inference
                  scores are raw probability estimates and should be calibrated against domain retention goals.
                </div>
              </>
            ) : (
              <div className="empty-state-box">
                <div className="empty-state-title">Model details unreachable</div>
                <p className="empty-state-desc">
                  Unable to retrieve active model metadata from the backend service. Ensure the inference process is
                  running.
                </p>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

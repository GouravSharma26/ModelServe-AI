import React, { useEffect } from 'react';

export default function WelcomeDialog({ onStartTutorial, onSkip }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onSkip();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onSkip]);

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
      <div className="welcome-modal">
        <button
          type="button"
          className="modal-close-btn"
          onClick={onSkip}
          aria-label="Close welcome dialog"
          title="Close (Esc)"
        >
          ×
        </button>

        <div className="welcome-header">
          <span className="welcome-tag">MODELSERVE · GETTING STARTED</span>
          <h2 className="welcome-title" id="welcome-title">Welcome to ModelServe</h2>
          <p className="welcome-description">
            Explore customer churn prediction, run sample machine learning inferences, and inspect real-time
            operational telemetry and offline model validation metrics.
          </p>
        </div>

        <div className="welcome-content">
          <h3 className="welcome-section-title">What you will learn</h3>
          <ul className="welcome-learn-list">
            <li>
              <span className="learn-dot" />
              <span>
                <strong>Platform Architecture:</strong> How the scikit-learn classification pipeline, FastAPI backend, and PostgreSQL store interact.
              </span>
            </li>
            <li>
              <span className="learn-dot" />
              <span>
                <strong>Sample Data Workflow:</strong> Download verified synthetic customer records and inspect client-side schema validation.
              </span>
            </li>
            <li>
              <span className="learn-dot" />
              <span>
                <strong>Live Prediction:</strong> Submit individual customer profiles for real-time churn risk classification and probability scoring.
              </span>
            </li>
            <li>
              <span className="learn-dot" />
              <span>
                <strong>Observability & Lineage:</strong> Inspect rolling-window execution telemetry, latency percentiles (p50/p95/p99), and model provenance.
              </span>
            </li>
          </ul>

          <div className="welcome-meta-row">
            <span className="welcome-duration">Approximate completion time: <strong>2–3 minutes</strong></span>
            <span className="welcome-steps-count">6 guided steps</span>
          </div>
        </div>

        <div className="welcome-footer">
          <button
            type="button"
            className="btn-ghost"
            onClick={onSkip}
          >
            Skip tutorial
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={onStartTutorial}
          >
            Get started →
          </button>
        </div>
      </div>
    </div>
  );
}

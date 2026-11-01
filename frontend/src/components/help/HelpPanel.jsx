import React, { useState, useEffect, useRef, useMemo } from 'react';

const API_DOCS_URL = 'https://modelserve-ai.onrender.com/docs';

export const HELP_SECTIONS = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    badge: 'Quickstart',
    topics: [
      {
        id: 'what-is-modelserve',
        question: 'What is ModelServe?',
        answer:
          'ModelServe AI is a production-oriented machine learning inference platform for customer churn classification. It demonstrates a complete, reliable path from reproducible scikit-learn training to validated REST API inference, durable PostgreSQL persistence, operational telemetry monitoring, and an enterprise analytics dashboard.',
      },
      {
        id: 'how-to-start-tutorial',
        question: 'How do I take the guided tour?',
        answer:
          'Click the "Start Guided Tutorial" button above at any time. The interactive 6-step walkthrough highlights system status indicators, sample data workflows, real-time prediction inputs, PostgreSQL latency metrics, and model provenance.',
      },
      {
        id: 'download-sample-data',
        question: 'How do I download sample customer data?',
        answer:
          'In the Inference Playground section, click the "Download sample CSV" button. This downloads demo-customers.csv, which contains 5 pre-configured synthetic customer profiles structured with the exact 19 feature columns required by the model.',
      },
      {
        id: 'upload-customer-csv',
        question: 'How do I upload and validate a customer CSV?',
        answer:
          'Click "Upload CSV" in the Sample Data section. The file is parsed and validated entirely inside your browser against expected column names, numerical ranges, and categorical constraints. No data is sent to the server until you select an individual customer record and click "Run prediction".',
      },
    ],
  },
  {
    id: 'prediction-guide',
    title: 'Prediction Guide',
    badge: 'Inference',
    topics: [
      {
        id: 'how-churn-works',
        question: 'How does customer churn prediction work?',
        answer:
          'Customer churn occurs when a subscriber cancels or terminates their service. The model assesses customer demographics, subscribed products, contract types, and billing history to estimate the empirical probability that a customer will discontinue service.',
      },
      {
        id: 'required-features',
        question: 'What customer features are required by the model?',
        answer:
          'The model strictly requires 19 customer features: gender, SeniorCitizen, Partner, Dependents, tenure, PhoneService, MultipleLines, InternetService, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, Contract, PaperlessBilling, PaymentMethod, MonthlyCharges, and TotalCharges. Extra unexpected fields are forbidden by schema policy (HTTP 422) to prevent silent data corruption.',
      },
      {
        id: 'churn-probability',
        question: 'What does the churn probability score represent?',
        answer:
          'The score is a continuous probability estimate between 0.00 and 1.00 (0% to 100%) produced by the model pipeline\'s logistic sigmoid function, representing the predicted likelihood of contract cancellation.',
      },
      {
        id: 'retained-vs-churn',
        question: 'How are "Retained" and "High Churn Risk" determined?',
        answer:
          'The platform uses a calibrated decision threshold of 0.50. Predictions with probability score >= 0.50 are labeled "High Churn Risk" (Yes) and flagged for proactive retention outreach. Predictions with score < 0.50 are labeled "Retained Customer" (No).',
      },
      {
        id: 'submitting-prediction',
        question: 'What happens when I submit a prediction?',
        answer:
          'The frontend sends a validated JSON request with an X-Request-ID header to POST /v1/predictions. The FastAPI service deserializes the request, validates all fields with Pydantic, evaluates the scikit-learn pipeline, stores inference telemetry asynchronously in PostgreSQL, and returns the classification result, probability score, model metadata, and latency.',
      },
    ],
  },
  {
    id: 'monitoring-telemetry',
    title: 'Monitoring & Telemetry',
    badge: 'Observability',
    topics: [
      {
        id: 'what-is-telemetry',
        question: 'What is inference telemetry?',
        answer:
          'Inference telemetry is the real-time operational logging of model performance signals, prediction distribution shifts, and request latencies stored durably in PostgreSQL to ensure the production serving engine meets service level objectives (SLOs).',
      },
      {
        id: 'prediction-volume',
        question: 'How is prediction volume measured?',
        answer:
          'Prediction volume reflects the count of inference transactions persisted within the selected rolling time window (1 hour, 6 hours, 24 hours, 72 hours, or 7 days). It is dynamically queried via GET /v1/monitoring/summary.',
      },
      {
        id: 'churn-distribution',
        question: 'What does the churn distribution show?',
        answer:
          'The churn distribution compares the percentage and count of positive churn alerts (Yes) against retained predictions (No). A sudden increase in predicted churn rate may signal changes in marketing traffic, pricing updates, or seasonal churn spikes.',
      },
      {
        id: 'mean-churn-probability',
        question: 'What is the mean churn probability?',
        answer:
          'The arithmetic mean of all continuous prediction scores recorded across the active time window. It summarizes overall customer portfolio risk independently of the binary decision threshold.',
      },
      {
        id: 'latency-percentiles',
        question: 'What are p50, p95, and p99 latency percentiles?',
        answer:
          'These represent execution time thresholds: p50 (median) means 50% of requests executed faster than this duration; p95 captures typical service responsiveness (95% faster); and p99 measures tail latency, exposing worst-case performance under peak load.',
      },
      {
        id: 'database-persistence',
        question: 'How are telemetry records persisted?',
        answer:
          'Telemetry is durably stored in PostgreSQL using SQLAlchemy 2.0 and Alembic schema migrations. To preserve customer privacy and enforce data minimization (ADR-008), raw input feature values are not persisted—only metadata, scores, labels, and latency measurements are retained.',
      },
    ],
  },
  {
    id: 'model-information',
    title: 'Model Information',
    badge: 'ML Engine',
    topics: [
      {
        id: 'logistic-regression',
        question: 'What is Logistic Regression in this platform?',
        answer:
          'ModelServe AI uses a regularized Logistic Regression classifier fit inside an end-to-end scikit-learn pipeline with median imputation, one-hot encoding, and standard scaling. It offers transparent feature interpretability, bounded probabilistic scores, and sub-millisecond execution times.',
      },
      {
        id: 'pr-auc',
        question: 'What is PR-AUC (Average Precision)?',
        answer:
          'Precision-Recall Area Under the Curve (held-out score: 0.6232) is our primary model selection rule. In customer churn datasets where churners are the minority class (~26%), PR-AUC evaluates precision and recall trade-offs more reliably than ROC-AUC.',
      },
      {
        id: 'roc-auc',
        question: 'What is ROC-AUC?',
        answer:
          'Receiver Operating Characteristic Area Under Curve (held-out score: 0.8321) measures the model\'s capability to discriminate between positive churners and negative retained customers across all possible decision thresholds.',
      },
      {
        id: 'f1-score',
        question: 'What is the F1 score?',
        answer:
          'The harmonic mean of precision and recall (held-out score: 0.6247 at threshold 0.50). It balances false positives (unnecessary retention offers) against false negatives (undetected churning subscribers).',
      },
      {
        id: 'decision-threshold',
        question: 'What is the decision threshold?',
        answer:
          'The cutoff point (0.50) applied to the continuous churn probability to assign the categorical label. This threshold can be adjusted by business retention teams depending on the cost of customer acquisition versus retention incentives.',
      },
      {
        id: 'confusion-matrix',
        question: 'How is the confusion matrix structured?',
        answer:
          'Evaluated on an offline 20% stratified test split of 1,409 rows: True Negatives: 742, False Positives: 293, False Negatives: 71, True Positives: 303. This confirms high recall on churning customers with reliable discrimination.',
      },
      {
        id: 'model-provenance',
        question: 'What is the model provenance and versioning policy?',
        answer:
          'Trained reproducibly from IBM\'s public Telco Customer Churn sample (Apache-2.0 license). Every model artifact is cryptographically hashed (SHA-256) and verified against manifest.json before the FastAPI inference engine loads it into memory.',
      },
    ],
  },
  {
    id: 'system-architecture',
    title: 'System Architecture',
    badge: 'Infrastructure',
    topics: [
      {
        id: 'platform-pipeline',
        question: 'How is the platform structured end-to-end?',
        answer:
          'ModelServe AI follows a modular monolith architecture: React + Vite frontend communicates over CORS-enabled REST with a FastAPI backend. The backend evaluates the in-memory scikit-learn pipeline and records inference telemetry asynchronously into PostgreSQL.',
      },
      {
        id: 'deployed-services',
        question: 'Where are the platform services deployed?',
        answer:
          'The live production deployment runs across three serverless/managed cloud tiers: (1) Frontend on Vercel Global Edge CDN, (2) Inference API on Render Web Services via Docker, and (3) Telemetry Database on Neon Serverless PostgreSQL with SSL.',
      },
      {
        id: 'api-documentation',
        question: 'Where can I inspect the interactive REST API documentation?',
        answer:
          'You can inspect and execute all live endpoints (predictions, health checks, model info, monitoring summary) through the official OpenAPI Swagger UI at https://modelserve-ai.onrender.com/docs.',
      },
    ],
  },
];

export default function HelpPanel({ isOpen, onClose, onRestartTutorial }) {
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [openTopicId, setOpenTopicId] = useState('what-is-modelserve');
  const panelRef = useRef(null);

  // Filter sections and topics based on category and search query
  const filteredSections = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return HELP_SECTIONS.map((sec) => {
      if (activeCategory !== 'all' && sec.id !== activeCategory) {
        return null;
      }

      if (!query) {
        return sec;
      }

      const matchingTopics = sec.topics.filter(
        (t) =>
          t.question.toLowerCase().includes(query) ||
          t.answer.toLowerCase().includes(query)
      );

      if (matchingTopics.length === 0) return null;

      return {
        ...sec,
        topics: matchingTopics,
      };
    }).filter(Boolean);
  }, [activeCategory, searchQuery]);

  // Total topics count
  const totalTopicsCount = useMemo(() => {
    return filteredSections.reduce((acc, sec) => acc + sec.topics.length, 0);
  }, [filteredSections]);

  // Focus management and keyboard dismiss
  useEffect(() => {
    if (!isOpen) return;

    // Focus panel container on open for screen readers
    const currentPanel = panelRef.current;
    if (currentPanel) {
      currentPanel.focus();
    }

    const handleOutsideClick = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        // Prevent immediate toggle if the click was on the trigger button itself
        const trigger = document.getElementById('floating-help-trigger');
        if (trigger && trigger.contains(e.target)) return;

        onClose();
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
        // Return focus to trigger button
        const trigger = document.getElementById('floating-help-trigger');
        if (trigger) trigger.focus();
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      id="help-panel"
      className="help-panel"
      ref={panelRef}
      role="dialog"
      aria-labelledby="help-panel-title"
      aria-modal="false"
      tabIndex={-1}
    >
      {/* Panel Header */}
      <div className="help-panel-header">
        <div>
          <div className="help-panel-tag">DOCUMENTATION & ARCHITECTURE</div>
          <h3 className="help-panel-title" id="help-panel-title">
            Help & Documentation
          </h3>
          <p className="help-panel-subtitle">
            ModelServe AI platform guide, ML definitions & operational concepts
          </p>
        </div>
        <button
          type="button"
          className="help-close-btn"
          onClick={() => {
            onClose();
            const trigger = document.getElementById('floating-help-trigger');
            if (trigger) trigger.focus();
          }}
          aria-label="Close help panel"
          title="Close (Esc)"
        >
          ×
        </button>
      </div>

      {/* Action Bar: Start Guided Tour & API Docs */}
      <div className="help-panel-actions-grid">
        <button
          type="button"
          className="btn-primary btn-sm btn-full"
          onClick={() => {
            onClose();
            onRestartTutorial();
          }}
          title="Restart the 6-step interactive onboarding walkthrough"
        >
          Start Guided Tour
        </button>

        <a
          href={API_DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary btn-sm btn-full text-center"
          title="Open interactive OpenAPI Swagger documentation in a new tab"
        >
          API Docs (Swagger) ↗
        </a>
      </div>

      {/* Search Input */}
      <div className="help-search-wrap">
        <input
          type="search"
          className="help-search-input"
          placeholder="Search guides, metrics, architecture..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search documentation topics"
        />
        {searchQuery && (
          <button
            type="button"
            className="help-search-clear"
            onClick={() => setSearchQuery('')}
            aria-label="Clear search"
          >
            ×
          </button>
        )}
      </div>

      {/* Category Tabs */}
      <div className="help-category-nav" role="tablist" aria-label="Documentation sections">
        <button
          type="button"
          role="tab"
          aria-selected={activeCategory === 'all'}
          className={`help-cat-pill ${activeCategory === 'all' ? 'is-active' : ''}`}
          onClick={() => setActiveCategory('all')}
        >
          All
        </button>
        {HELP_SECTIONS.map((sec) => (
          <button
            key={sec.id}
            type="button"
            role="tab"
            aria-selected={activeCategory === sec.id}
            className={`help-cat-pill ${activeCategory === sec.id ? 'is-active' : ''}`}
            onClick={() => setActiveCategory(sec.id)}
          >
            {sec.badge}
          </button>
        ))}
      </div>

      {/* Accordion Topics List */}
      <div className="help-accordion" role="region" aria-label="Help topics list">
        {totalTopicsCount === 0 ? (
          <div className="help-empty-search">
            <span className="text-muted">No documentation topics match "{searchQuery}".</span>
            <button
              type="button"
              className="btn-ghost btn-sm"
              onClick={() => {
                setSearchQuery('');
                setActiveCategory('all');
              }}
            >
              Reset search
            </button>
          </div>
        ) : (
          filteredSections.map((sec) => (
            <div key={sec.id} className="help-section-group">
              <div className="help-section-header">
                <span className="help-section-title">{sec.title}</span>
                <span className="help-section-count">{sec.topics.length}</span>
              </div>

              <div className="help-section-topics">
                {sec.topics.map((topic) => {
                  const isExpanded = openTopicId === topic.id;
                  const triggerId = `help-trigger-${topic.id}`;
                  const contentId = `help-content-${topic.id}`;

                  return (
                    <div
                      key={topic.id}
                      className={`help-topic-item ${isExpanded ? 'is-expanded' : ''}`}
                    >
                      <button
                        type="button"
                        id={triggerId}
                        className="help-topic-trigger"
                        onClick={() => setOpenTopicId(isExpanded ? null : topic.id)}
                        aria-expanded={isExpanded}
                        aria-controls={contentId}
                      >
                        <span className="help-question-text">{topic.question}</span>
                        <span className="help-expand-icon" aria-hidden="true">
                          {isExpanded ? '−' : '+'}
                        </span>
                      </button>

                      {isExpanded && (
                        <div
                          id={contentId}
                          role="region"
                          aria-labelledby={triggerId}
                          className="help-topic-content"
                        >
                          <p>{topic.answer}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="help-panel-footer">
        <span className="text-muted">
          Press <strong>Esc</strong> or click outside to dismiss
        </span>
      </div>
    </div>
  );
}

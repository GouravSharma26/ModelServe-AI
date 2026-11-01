import React, { useState, useEffect, useRef } from 'react';

const HELP_TOPICS = [
  {
    id: 'about',
    question: 'What is ModelServe?',
    answer:
      'ModelServe AI is a production-oriented machine learning inference platform designed to classify customer churn risk. It integrates a scikit-learn pipeline, a FastAPI REST service, persistent PostgreSQL telemetry tracking, and an interactive React analytics dashboard.',
  },
  {
    id: 'churn-prediction',
    question: 'How does churn prediction work?',
    answer:
      'Customer churn occurs when a subscriber discontinues their service. The model processes 19 demographic, subscribed service, and billing attributes (e.g. Contract type, MonthlyCharges, Tenure, InternetService) to compute a calibrated probability of customer churn.',
  },
  {
    id: 'sample-data',
    question: 'How do I download sample data and test CSVs?',
    answer:
      'Click "Download sample CSV" in the Inference Playground or within the guided tutorial. This downloads demo-customers.csv containing pre-configured synthetic customer profiles with valid schemas ready for instant testing.',
  },
  {
    id: 'upload-csv',
    question: 'How do I upload a CSV and test multiple customers?',
    answer:
      'Click "Upload CSV" in the Sample Data section. The file is validated locally in your browser against required column types and categorical values. Once validated, select any customer record from the preview table to populate the form and run inference.',
  },
  {
    id: 'probability-score',
    question: 'What does the churn probability score mean?',
    answer:
      'The score represents the estimated likelihood of churn (from 0.0 to 1.0). With a decision threshold of 0.5, predictions with a score >= 0.5 are classified as "High Churn Risk" (Yes), while scores below 0.5 are classified as "Retained" (No).',
  },
  {
    id: 'latency-percentiles',
    question: 'What are p50, p95, and p99 latency metrics?',
    answer:
      'These represent execution duration percentiles persisted in PostgreSQL. p50 is median response time, while p95 and p99 measure tail latency—meaning 95% and 99% of inference requests resolved faster than the reported millisecond values.',
  },
  {
    id: 'evaluation-metrics',
    question: 'What do PR-AUC and ROC-AUC mean?',
    answer:
      'PR-AUC (Precision-Recall Area Under Curve / Average Precision) is our primary selection metric because churn datasets are class-imbalanced. ROC-AUC evaluates the trade-off between True Positive Rate and False Positive Rate across all decision thresholds.',
  },
];

export default function HelpPanel({ isOpen, onClose, onRestartTutorial }) {
  const [openTopicId, setOpenTopicId] = useState('about');
  const panelRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleOutsideClick = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        // Check if the click was on the floating trigger button itself
        const trigger = document.getElementById('floating-help-trigger');
        if (trigger && trigger.contains(e.target)) return;

        onClose();
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
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
      className="help-panel"
      ref={panelRef}
      role="dialog"
      aria-labelledby="help-panel-title"
      aria-modal="false"
    >
      <div className="help-panel-header">
        <div>
          <h3 className="help-panel-title" id="help-panel-title">Help & Documentation</h3>
          <p className="help-panel-subtitle">ModelServe guides, ML definitions & operational concepts</p>
        </div>
        <button
          type="button"
          className="help-close-btn"
          onClick={onClose}
          aria-label="Close help panel"
          title="Close (Esc)"
        >
          ×
        </button>
      </div>

      <div className="help-panel-actions">
        <button
          type="button"
          className="btn-secondary btn-full"
          onClick={() => {
            onRestartTutorial();
            onClose();
          }}
        >
          Restart Guided Tutorial
        </button>
      </div>

      <div className="help-accordion">
        {HELP_TOPICS.map((topic) => {
          const isExpanded = openTopicId === topic.id;
          return (
            <div
              key={topic.id}
              className={`help-topic-item ${isExpanded ? 'is-expanded' : ''}`}
            >
              <button
                type="button"
                className="help-topic-trigger"
                onClick={() => setOpenTopicId(isExpanded ? null : topic.id)}
                aria-expanded={isExpanded}
              >
                <span>{topic.question}</span>
                <span className="help-expand-icon">{isExpanded ? '−' : '+'}</span>
              </button>
              {isExpanded && (
                <div className="help-topic-content">
                  <p>{topic.answer}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="help-panel-footer">
        <span className="text-muted">Press <strong>Esc</strong> or click outside to dismiss</span>
      </div>
    </div>
  );
}

import React, { useEffect, useState, useCallback, useRef } from 'react';

const TUTORIAL_STEPS = [
  {
    step: 1,
    title: 'Understanding the Platform',
    tab: 'prediction',
    targetSelector: '.status-grid',
    description:
      'ModelServe AI serves real-time machine learning predictions for customer churn. The status indicators above report the live health of the API process, the inference engine, and the cryptographically verified model artifact.',
    actionHint: 'Notice the API Process and Inference Engine indicators.',
  },
  {
    step: 2,
    title: 'Download Sample Dataset',
    tab: 'prediction',
    targetSelector: '#btn-download-sample-csv',
    description:
      'To test predictions without manually entering 19 customer features, download our synthetic customer dataset. It contains realistic customer profiles with varied contract types, tenure, and billing details.',
    actionHint: 'Click "Download sample CSV" or proceed to the next step.',
  },
  {
    step: 3,
    title: 'Upload and Validate Records',
    tab: 'prediction',
    targetSelector: '#csv-workflow-section',
    description:
      'Upload any CSV of customer profiles. The frontend parses and validates all 19 model features locally in your browser—no data is uploaded or stored on the server until you choose to predict.',
    actionHint: 'Upload demo-customers.csv to see the interactive customer preview table.',
  },
  {
    step: 4,
    title: 'Run a Real Prediction',
    tab: 'prediction',
    targetSelector: '.form-submit-row',
    description:
      'Select a customer from the preview table or adjust the feature inputs in the playground, then click "Run prediction". The request is evaluated by the live scikit-learn model on Render.',
    actionHint: 'Run inference to generate a churn risk probability score.',
  },
  {
    step: 5,
    title: 'Explore Inference Telemetry',
    tab: 'telemetry',
    targetSelector: '.telemetry-controls',
    description:
      'Every inference event is recorded in PostgreSQL. The Telemetry dashboard calculates rolling-window prediction volumes, churn rates, and execution latency percentiles (p50, p95, p99) in real time.',
    actionHint: 'Select different aggregation windows (1h, 24h, 7d) to inspect historical metrics.',
  },
  {
    step: 6,
    title: 'Model Evaluation & Provenance',
    tab: 'model-info',
    targetSelector: '.stats-metric-grid',
    description:
      'Inspect model lineage, the IBM Telco Churn training provenance, and offline benchmark evaluations including held-out PR-AUC, ROC-AUC, F1 score, and the confusion matrix.',
    actionHint: 'Review benchmark performance metrics and dataset cryptographic checksums.',
  },
];

export default function TutorialController({
  activeTab,
  onTabChange,
  onComplete,
  onExit,
  currentStep,
  setCurrentStep,
}) {
  const [targetRect, setTargetRect] = useState(null);
  const cardRef = useRef(null);

  const stepData = TUTORIAL_STEPS[currentStep - 1] || TUTORIAL_STEPS[0];

  // Ensure appropriate tab is open for the current step
  useEffect(() => {
    if (stepData.tab && activeTab !== stepData.tab) {
      onTabChange(stepData.tab);
    }
  }, [currentStep, stepData.tab, activeTab, onTabChange]);

  // Measure and highlight target element
  const updateTargetPosition = useCallback(() => {
    if (!stepData.targetSelector) {
      setTargetRect(null);
      return;
    }

    const el = document.querySelector(stepData.targetSelector);
    if (el) {
      const rect = el.getBoundingClientRect();
      setTargetRect({
        top: rect.top + window.scrollY,
        left: rect.left + window.scrollX,
        width: rect.width,
        height: rect.height,
        bottom: rect.bottom + window.scrollY,
      });

      // Smoothly scroll target into view if needed
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      setTargetRect(null);
    }
  }, [stepData.targetSelector]);

  useEffect(() => {
    const timer = setTimeout(updateTargetPosition, 250);
    window.addEventListener('resize', updateTargetPosition);
    window.addEventListener('scroll', updateTargetPosition);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', updateTargetPosition);
      window.removeEventListener('scroll', updateTargetPosition);
    };
  }, [updateTargetPosition, activeTab, currentStep]);

  const handleNext = () => {
    if (currentStep < TUTORIAL_STEPS.length) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="tutorial-overlay-wrapper">
      {/* Target element spotlight outline */}
      {targetRect && (
        <div
          className="tutorial-spotlight"
          style={{
            top: `${targetRect.top - 6}px`,
            left: `${targetRect.left - 6}px`,
            width: `${targetRect.width + 12}px`,
            height: `${targetRect.height + 12}px`,
          }}
        />
      )}

      {/* Docked Tutorial Navigation Card */}
      <div
        className="tutorial-card"
        ref={cardRef}
        role="region"
        aria-label="Interactive tutorial guide"
      >
        <div className="tutorial-card-header">
          <div className="tutorial-step-badge">
            Step {currentStep} of {TUTORIAL_STEPS.length}
          </div>
          <button
            type="button"
            className="tutorial-close-btn"
            onClick={onExit}
            title="Exit tutorial (Esc)"
            aria-label="Exit tutorial"
          >
            ×
          </button>
        </div>

        {/* Progress bar */}
        <div className="tutorial-progress-track">
          <div
            className="tutorial-progress-fill"
            style={{ width: `${(currentStep / TUTORIAL_STEPS.length) * 100}%` }}
          />
        </div>

        <div className="tutorial-body">
          <h4 className="tutorial-title">{stepData.title}</h4>
          <p className="tutorial-desc">{stepData.description}</p>
          <div className="tutorial-action-hint">
            <strong>Tip:</strong> {stepData.actionHint}
          </div>
        </div>

        <div className="tutorial-footer">
          <div className="tutorial-left-actions">
            <button
              type="button"
              className="btn-ghost"
              onClick={handlePrev}
              disabled={currentStep === 1}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={onExit}
              title="Skip remaining steps"
            >
              Exit
            </button>
          </div>

          <div className="tutorial-right-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={handleNext}
            >
              {currentStep === TUTORIAL_STEPS.length ? 'Finish tutorial' : 'Next step →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

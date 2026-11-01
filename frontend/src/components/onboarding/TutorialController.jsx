import React, { useEffect, useState, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';

const TUTORIAL_STEPS = [
  {
    step: 1,
    title: 'Understanding the Platform',
    tab: 'prediction',
    targetSelector: '.status-grid',
    description:
      'ModelServe AI serves real-time machine learning predictions for customer churn. The status indicators above report the live health of the API process, the inference engine, and the cryptographically verified model artifact.',
    actionHint: 'Notice the API Process and Inference Engine status cards.',
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
    targetSelector: '#btn-upload-csv-trigger',
    description:
      'Upload any CSV of customer profiles. The frontend parses and validates all 19 model features locally in your browser—no data is uploaded or stored on the server until you choose to predict.',
    actionHint: 'Click "Upload CSV" to select a customer profile from the preview table.',
  },
  {
    step: 4,
    title: 'Run a Real Prediction',
    tab: 'prediction',
    targetSelector: '.form-submit-row .btn-primary',
    description:
      'Select a customer from the preview table or adjust the feature inputs in the playground, then click "Run prediction". The request is evaluated by the live scikit-learn model on Render.',
    actionHint: 'Click "Run prediction" to generate a churn risk probability score.',
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
  predictionResult,
}) {
  const [targetRect, setTargetRect] = useState(null);
  const [actionBlockedMsg, setActionBlockedMsg] = useState(null);
  const cardRef = useRef(null);

  const stepData = TUTORIAL_STEPS[currentStep - 1] || TUTORIAL_STEPS[0];

  // Clear any action blocked error when step changes or prediction completes
  useEffect(() => {
    setActionBlockedMsg(null);
  }, [currentStep, predictionResult]);

  // Ensure appropriate tab is open for the current step
  useEffect(() => {
    if (stepData.tab && activeTab !== stepData.tab) {
      onTabChange(stepData.tab);
    }
  }, [currentStep, stepData.tab, activeTab, onTabChange]);

  // Measure target element in viewport coordinates (position: fixed)
  const updateTargetPosition = useCallback(() => {
    if (!stepData.targetSelector) {
      setTargetRect(null);
      return;
    }

    const el = document.querySelector(stepData.targetSelector);
    if (el) {
      const rect = el.getBoundingClientRect();
      setTargetRect({
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      });
    } else {
      setTargetRect(null);
    }
  }, [stepData.targetSelector]);

  // When step or tab changes, scroll target element into view smoothly and track it
  useEffect(() => {
    let animationFrameId;
    let startTime = null;

    const el = document.querySelector(stepData.targetSelector);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Repeatedly track element position while smooth scrolling occurs (400ms duration)
    const trackSmoothScroll = (timestamp) => {
      if (!startTime) startTime = timestamp;
      updateTargetPosition();
      if (timestamp - startTime < 450) {
        animationFrameId = requestAnimationFrame(trackSmoothScroll);
      }
    };

    animationFrameId = requestAnimationFrame(trackSmoothScroll);

    // Also poll at defined intervals to catch asynchronous DOM updates (e.g. tab switches)
    const timer1 = setTimeout(updateTargetPosition, 80);
    const timer2 = setTimeout(updateTargetPosition, 200);
    const timer3 = setTimeout(updateTargetPosition, 400);

    return () => {
      cancelAnimationFrame(animationFrameId);
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [currentStep, activeTab, stepData.targetSelector, updateTargetPosition]);

  // Track window scroll and resize continuously
  useEffect(() => {
    const handleScrollOrResize = () => {
      updateTargetPosition();
    };

    window.addEventListener('scroll', handleScrollOrResize, { passive: true });
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      window.removeEventListener('scroll', handleScrollOrResize);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [updateTargetPosition]);

  const handleNext = useCallback(() => {
    if (currentStep === 4 && !predictionResult) {
      setActionBlockedMsg('Please run a prediction first to generate inference results before exploring telemetry.');
      return;
    }
    setActionBlockedMsg(null);
    if (currentStep < TUTORIAL_STEPS.length) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  }, [currentStep, predictionResult, setCurrentStep, onComplete]);

  const handlePrev = useCallback(() => {
    setActionBlockedMsg(null);
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep, setCurrentStep]);

  // Keyboard controls: Escape exits, ArrowRight advances, ArrowLeft goes back
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onExit();
      } else if (e.key === 'ArrowRight') {
        handleNext();
      } else if (e.key === 'ArrowLeft') {
        handlePrev();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNext, handlePrev, onExit]);

  const content = (
    <div className="tutorial-overlay-wrapper">
      {/* Target element spotlight outline with full-screen backdrop cutout */}
      {targetRect && (
        <div
          className="tutorial-spotlight"
          style={{
            top: `${Math.round(targetRect.top - 6)}px`,
            left: `${Math.round(targetRect.left - 6)}px`,
            width: `${Math.round(targetRect.width + 12)}px`,
            height: `${Math.round(targetRect.height + 12)}px`,
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
          {actionBlockedMsg && (
            <div className="tutorial-blocked-alert" role="alert">
              <strong>Action Required:</strong> {actionBlockedMsg}
            </div>
          )}
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

  return typeof document !== 'undefined' ? createPortal(content, document.body) : null;
}

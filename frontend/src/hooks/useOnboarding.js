import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY_DISMISSED = 'modelserve_onboarding_dismissed';
const STORAGE_KEY_COMPLETED = 'modelserve_onboarding_completed';

export function useOnboarding() {
  const [showWelcome, setShowWelcome] = useState(false);
  const [tutorialActive, setTutorialActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);

  useEffect(() => {
    try {
      const dismissed = localStorage.getItem(STORAGE_KEY_DISMISSED);
      if (dismissed !== 'true') {
        setShowWelcome(true);
      }
    } catch {
      // In case localStorage is disabled/restricted in iframe
      setShowWelcome(false);
    }
  }, []);

  const startTutorial = useCallback(() => {
    setShowWelcome(false);
    setTutorialActive(true);
    setCurrentStep(1);
  }, []);

  const skipTutorial = useCallback(() => {
    setShowWelcome(false);
    setTutorialActive(false);
    try {
      localStorage.setItem(STORAGE_KEY_DISMISSED, 'true');
    } catch {
      // Ignore storage errors
    }
  }, []);

  const completeTutorial = useCallback(() => {
    setTutorialActive(false);
    try {
      localStorage.setItem(STORAGE_KEY_DISMISSED, 'true');
      localStorage.setItem(STORAGE_KEY_COMPLETED, 'true');
    } catch {
      // Ignore storage errors
    }
  }, []);

  const exitTutorial = useCallback(() => {
    setTutorialActive(false);
    try {
      localStorage.setItem(STORAGE_KEY_DISMISSED, 'true');
    } catch {
      // Ignore storage errors
    }
  }, []);

  const restartTutorial = useCallback(() => {
    setShowWelcome(false);
    setTutorialActive(true);
    setCurrentStep(1);
  }, []);

  return {
    showWelcome,
    tutorialActive,
    currentStep,
    setCurrentStep,
    startTutorial,
    skipTutorial,
    completeTutorial,
    exitTutorial,
    restartTutorial,
  };
}


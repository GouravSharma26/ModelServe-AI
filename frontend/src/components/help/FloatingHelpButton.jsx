import React, { useState, useEffect } from 'react';
import HelpPanel from './HelpPanel';

export default function FloatingHelpButton({ onRestartTutorial, tutorialActive }) {
  const [isOpen, setIsOpen] = useState(false);

  // Close help panel automatically if the guided tutorial becomes active
  useEffect(() => {
    if (tutorialActive && isOpen) {
      setIsOpen(false);
    }
  }, [tutorialActive, isOpen]);

  const togglePanel = () => {
    setIsOpen((prev) => !prev);
  };

  return (
    <>
      <button
        type="button"
        id="floating-help-trigger"
        className={`floating-help-btn ${isOpen ? 'is-active' : ''}`}
        onClick={togglePanel}
        aria-label={isOpen ? 'Close Help and Documentation' : 'Open Help and Documentation'}
        aria-expanded={isOpen}
        aria-controls="help-panel"
        aria-haspopup="dialog"
        title={isOpen ? 'Close Help (Esc)' : 'Help & Documentation (?)'}
      >
        <span className="help-icon-text">{isOpen ? '×' : '?'}</span>
      </button>

      <HelpPanel
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onRestartTutorial={onRestartTutorial}
      />
    </>
  );
}

import React, { useState } from 'react';
import HelpPanel from './HelpPanel';

export default function FloatingHelpButton({ onRestartTutorial }) {
  const [isOpen, setIsOpen] = useState(false);

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
        aria-label="Help and Documentation"
        title="Help and Documentation (?)"
      >
        <span className="help-icon-text">?</span>
      </button>

      <HelpPanel
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onRestartTutorial={onRestartTutorial}
      />
    </>
  );
}


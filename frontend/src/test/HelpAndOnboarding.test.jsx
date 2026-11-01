import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FloatingHelpButton from '../components/help/FloatingHelpButton';
import HelpPanel from '../components/help/HelpPanel';
import WelcomeDialog from '../components/onboarding/WelcomeDialog';

describe('FloatingHelpButton & HelpPanel interactions', () => {
  it('opens and closes help panel via floating trigger button', () => {
    const onRestartTutorial = vi.fn();
    render(
      <FloatingHelpButton onRestartTutorial={onRestartTutorial} tutorialActive={false} />
    );

    const triggerBtn = screen.getByRole('button', { name: /open help and documentation/i });
    expect(triggerBtn).toHaveAttribute('aria-expanded', 'false');

    // Click to open
    fireEvent.click(triggerBtn);
    expect(triggerBtn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('dialog', { name: /help & documentation/i })).toBeInTheDocument();

    // Click again to close
    fireEvent.click(triggerBtn);
    expect(triggerBtn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('dialog', { name: /help & documentation/i })).not.toBeInTheDocument();
  });

  it('closes help panel automatically when tutorial becomes active', () => {
    const { rerender } = render(
      <FloatingHelpButton onRestartTutorial={vi.fn()} tutorialActive={false} />
    );

    // Open the panel
    const triggerBtn = screen.getByRole('button', { name: /open help and documentation/i });
    fireEvent.click(triggerBtn);
    expect(screen.getByRole('dialog', { name: /help & documentation/i })).toBeInTheDocument();

    // Rerender with tutorialActive = true
    rerender(
      <FloatingHelpButton onRestartTutorial={vi.fn()} tutorialActive={true} />
    );
    expect(screen.queryByRole('dialog', { name: /help & documentation/i })).not.toBeInTheDocument();
  });

  it('invokes onRestartTutorial and closes when "Start Guided Tour" is clicked', () => {
    const onRestart = vi.fn();
    const onClose = vi.fn();

    render(
      <HelpPanel isOpen={true} onClose={onClose} onRestartTutorial={onRestart} />
    );

    const tourBtn = screen.getByRole('button', { name: /start guided tour/i });
    fireEvent.click(tourBtn);

    expect(onClose).toHaveBeenCalled();
    expect(onRestart).toHaveBeenCalled();
  });

  it('filters topics by search query inside HelpPanel', () => {
    render(
      <HelpPanel isOpen={true} onClose={vi.fn()} onRestartTutorial={vi.fn()} />
    );

    const searchInput = screen.getByPlaceholderText(/search guides/i);
    fireEvent.change(searchInput, { target: { value: 'latency' } });

    // Should match Telemetry & Latency topic question
    expect(screen.getByText(/What are p50, p95, and p99 latency percentiles\?/i)).toBeInTheDocument();
    // Non-matching topic should not be rendered
    expect(screen.queryByText(/What is ModelServe\?/i)).not.toBeInTheDocument();
  });

  it('filters topics by category pill inside HelpPanel', () => {
    render(
      <HelpPanel isOpen={true} onClose={vi.fn()} onRestartTutorial={vi.fn()} />
    );

    const obsPill = screen.getByRole('tab', { name: 'Observability' });
    fireEvent.click(obsPill);

    expect(screen.getByText(/What is inference telemetry\?/i)).toBeInTheDocument();
    expect(screen.queryByText(/What customer features are required by the model\?/i)).not.toBeInTheDocument();
  });

  it('closes HelpPanel when Escape key is pressed', () => {
    const onClose = vi.fn();
    render(
      <HelpPanel isOpen={true} onClose={onClose} onRestartTutorial={vi.fn()} />
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});

describe('WelcomeDialog component', () => {
  it('triggers onStartTutorial when "Get started →" is clicked', () => {
    const onStart = vi.fn();
    const onSkip = vi.fn();

    render(<WelcomeDialog onStartTutorial={onStart} onSkip={onSkip} />);

    expect(screen.getByText(/Welcome to ModelServe/i)).toBeInTheDocument();
    expect(screen.getByText(/6 guided steps/i)).toBeInTheDocument();

    const startBtn = screen.getByRole('button', { name: /get started/i });
    fireEvent.click(startBtn);

    expect(onStart).toHaveBeenCalled();
    expect(onSkip).not.toHaveBeenCalled();
  });

  it('triggers onSkip when "Skip tutorial" is clicked or close button pressed', () => {
    const onStart = vi.fn();
    const onSkip = vi.fn();

    render(<WelcomeDialog onStartTutorial={onStart} onSkip={onSkip} />);

    const skipBtn = screen.getByRole('button', { name: /skip tutorial/i });
    fireEvent.click(skipBtn);

    expect(onSkip).toHaveBeenCalled();
    expect(onStart).not.toHaveBeenCalled();
  });
});

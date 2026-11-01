import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CsvWorkflow from '../components/prediction/CsvWorkflow';

const VALID_CSV_CONTENT = `customerID,gender,SeniorCitizen,Partner,Dependents,tenure,PhoneService,MultipleLines,InternetService,OnlineSecurity,OnlineBackup,DeviceProtection,TechSupport,StreamingTV,StreamingMovies,Contract,PaperlessBilling,PaymentMethod,MonthlyCharges,TotalCharges
DEMO-001,Female,0,Yes,No,1,No,No phone service,DSL,No,Yes,No,No,No,No,Month-to-month,Yes,Electronic check,29.85,29.85
DEMO-002,Male,0,Yes,Yes,34,Yes,Yes,DSL,Yes,No,Yes,No,No,No,One year,No,Mailed check,56.95,1889.50`;

const INVALID_CSV_CONTENT = `customerID,gender,tenure\nDEMO-001,Female,1`;

function createMockFile(content, fileName = 'test.csv') {
  return new File([content], fileName, { type: 'text/csv' });
}

describe('CsvWorkflow component', () => {
  it('renders download link and upload trigger button', () => {
    render(<CsvWorkflow onSelectCustomer={vi.fn()} onRunPrediction={vi.fn()} />);

    expect(screen.getByText('Sample Data & Batch Inspection')).toBeInTheDocument();
    expect(screen.getByText('Download sample CSV')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload csv/i })).toBeInTheDocument();
  });

  it('parses valid CSV file, displays preview table, and auto-selects first row', async () => {
    const onSelectCustomer = vi.fn();
    render(<CsvWorkflow onSelectCustomer={onSelectCustomer} onRunPrediction={vi.fn()} />);

    const fileInput = document.querySelector('#csv-file-input');
    const file = createMockFile(VALID_CSV_CONTENT, 'customers.csv');

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('customers.csv')).toBeInTheDocument();
      expect(screen.getByText(/customer records parsed/i)).toBeInTheDocument();
    });

    // Both customer IDs should be rendered in table
    expect(screen.getByText('DEMO-001')).toBeInTheDocument();
    expect(screen.getByText('DEMO-002')).toBeInTheDocument();

    // First customer should have been selected
    expect(onSelectCustomer).toHaveBeenCalled();
    const firstCallArg = onSelectCustomer.mock.calls[0][0];
    expect(firstCallArg.id).toBe('DEMO-001');
    expect(firstCallArg.features.MonthlyCharges).toBe(29.85);
  });

  it('displays validation errors when an invalid CSV is uploaded', async () => {
    render(<CsvWorkflow onSelectCustomer={vi.fn()} onRunPrediction={vi.fn()} />);

    const fileInput = document.querySelector('#csv-file-input');
    const file = createMockFile(INVALID_CSV_CONTENT, 'invalid.csv');

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/CSV Validation Failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Missing required feature columns/i)).toBeInTheDocument();
    });

    // Preview table should not be displayed
    expect(screen.queryByText('DEMO-001')).not.toBeInTheDocument();
  });

  it('selects a different customer when clicking on a row', async () => {
    const onSelectCustomer = vi.fn();
    render(<CsvWorkflow onSelectCustomer={onSelectCustomer} onRunPrediction={vi.fn()} />);

    const fileInput = document.querySelector('#csv-file-input');
    fireEvent.change(fileInput, { target: { files: [createMockFile(VALID_CSV_CONTENT)] } });

    await waitFor(() => {
      expect(screen.getByText('DEMO-002')).toBeInTheDocument();
    });

    // Click row for DEMO-002
    const secondRow = screen.getByText('DEMO-002').closest('tr');
    fireEvent.click(secondRow);

    expect(onSelectCustomer).toHaveBeenLastCalledWith(
      expect.objectContaining({ id: 'DEMO-002' })
    );
  });

  it('triggers onRunPrediction when clicking Run inference button in table', async () => {
    const onRunPrediction = vi.fn();
    render(<CsvWorkflow onSelectCustomer={vi.fn()} onRunPrediction={onRunPrediction} />);

    const fileInput = document.querySelector('#csv-file-input');
    fireEvent.change(fileInput, { target: { files: [createMockFile(VALID_CSV_CONTENT)] } });

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /run inference/i })).toHaveLength(2);
    });

    const predictBtns = screen.getAllByRole('button', { name: /run inference/i });
    fireEvent.click(predictBtns[1]); // Click second customer's inference button

    expect(onRunPrediction).toHaveBeenCalledWith(
      expect.objectContaining({
        MonthlyCharges: 56.95,
        TotalCharges: 1889.5,
      })
    );
  });

  it('resets file and preview state when Clear button is clicked', async () => {
    render(<CsvWorkflow onSelectCustomer={vi.fn()} onRunPrediction={vi.fn()} />);

    const fileInput = document.querySelector('#csv-file-input');
    fireEvent.change(fileInput, { target: { files: [createMockFile(VALID_CSV_CONTENT)] } });

    await waitFor(() => {
      expect(screen.getByText('DEMO-001')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /clear/i }));

    await waitFor(() => {
      expect(screen.queryByText('DEMO-001')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /upload csv/i })).toBeInTheDocument();
    });
  });
});

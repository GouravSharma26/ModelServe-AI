import React, { useState, useRef } from 'react';
import { parseCsv } from '../../utils/csvParser';
import { validateCsvData } from '../../utils/csvValidation';

export default function CsvWorkflow({ onSelectCustomer, onRunPrediction, disabled }) {
  const [fileName, setFileName] = useState(null);
  const [records, setRecords] = useState([]);
  const [validationErrors, setValidationErrors] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setValidationErrors([]);
    setIsProcessing(true);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result;
        const { headers, rows } = parseCsv(text);
        const { valid, errors, validatedRows } = validateCsvData(headers, rows);

        if (!valid) {
          setValidationErrors(errors);
          setRecords([]);
          setSelectedId(null);
        } else {
          setRecords(validatedRows);
          setValidationErrors([]);
          if (validatedRows.length > 0) {
            setSelectedId(validatedRows[0].id);
            if (onSelectCustomer) {
              onSelectCustomer(validatedRows[0]);
            }
          }
        }
      } catch (err) {
        setValidationErrors([`Failed to parse CSV file: ${err.message}`]);
        setRecords([]);
        setSelectedId(null);
      } finally {
        setIsProcessing(false);
      }
    };

    reader.onerror = () => {
      setValidationErrors(['Error reading uploaded file. Please check file permissions.']);
      setIsProcessing(false);
    };

    reader.readAsText(file);
  };

  const handleClear = () => {
    setFileName(null);
    setRecords([]);
    setValidationErrors([]);
    setSelectedId(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRowClick = (record) => {
    setSelectedId(record.id);
    if (onSelectCustomer) {
      onSelectCustomer(record);
    }
  };

  const handleRunSelected = (e, record) => {
    e.stopPropagation();
    setSelectedId(record.id);
    if (onSelectCustomer) {
      onSelectCustomer(record);
    }
    if (onRunPrediction) {
      onRunPrediction(record.features);
    }
  };

  return (
    <div className="csv-workflow-card" id="csv-workflow-section">
      <div className="csv-header-row">
        <div>
          <h3 className="csv-title">Sample Data & Batch Inspection</h3>
          <p className="csv-subtitle">
            Upload synthetic customer profiles or download the verified demo dataset to test inference
          </p>
        </div>

        <div className="csv-actions-group">
          <a
            href="/demo-customers.csv"
            download="demo-customers.csv"
            className="btn-secondary-link"
            id="btn-download-sample-csv"
            title="Download verified synthetic customers CSV"
          >
            Download sample CSV
          </a>

          <input
            type="file"
            ref={fileInputRef}
            accept=".csv,text/csv"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
            id="csv-file-input"
          />

          <button
            type="button"
            className="btn-secondary"
            id="btn-upload-csv-trigger"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing || disabled}
          >
            {isProcessing ? 'Validating...' : fileName ? 'Replace CSV' : 'Upload CSV'}
          </button>

          {fileName && (
            <button
              type="button"
              className="btn-ghost"
              onClick={handleClear}
              title="Clear loaded file"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="banner-alert banner-alert-danger" role="alert" style={{ marginTop: '1rem' }}>
          <div className="banner-alert-title">CSV Validation Failed ({validationErrors.length} issue{validationErrors.length > 1 ? 's' : ''})</div>
          <ul className="banner-alert-list">
            {validationErrors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Loaded File Info & Table Preview */}
      {records.length > 0 && (
        <div className="csv-preview-container" id="csv-preview-table-container">
          <div className="csv-preview-meta">
            <span>
              Loaded: <strong>{fileName}</strong> · {records.length} customer records parsed
            </span>
            <span className="text-muted">
              Select a profile to load its attributes into the inference playground
            </span>
          </div>

          <div className="table-wrap">
            <table className="enterprise-table csv-records-table">
              <thead>
                <tr>
                  <th>Customer ID</th>
                  <th>Contract</th>
                  <th>Tenure</th>
                  <th>Monthly</th>
                  <th>Internet</th>
                  <th>Payment Method</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {records.map((rec) => {
                  const isSelected = selectedId === rec.id;
                  return (
                    <tr
                      key={rec.id}
                      className={isSelected ? 'row-selected' : ''}
                      onClick={() => handleRowClick(rec)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>
                        <span className="font-mono font-semibold text-accent">{rec.id}</span>
                        {isSelected && <span className="selection-badge">Selected</span>}
                      </td>
                      <td>{rec.features.Contract}</td>
                      <td className="font-mono">{rec.features.tenure} mo</td>
                      <td className="font-mono">${rec.features.MonthlyCharges.toFixed(2)}</td>
                      <td>{rec.features.InternetService}</td>
                      <td className="text-secondary">{rec.features.PaymentMethod}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          className={`btn-table-action ${isSelected ? 'btn-table-action-active' : ''}`}
                          onClick={(e) => handleRunSelected(e, rec)}
                          disabled={disabled}
                          title={`Run prediction for ${rec.id}`}
                        >
                          Run inference
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


/**
 * Schema definitions and validation logic for Telco Customer Churn CSV uploads.
 * Mirrors the exact Pydantic schema defined in src/modelserve/schemas.py.
 */

export const REQUIRED_MODEL_COLUMNS = [
  'gender',
  'SeniorCitizen',
  'Partner',
  'Dependents',
  'tenure',
  'PhoneService',
  'MultipleLines',
  'InternetService',
  'OnlineSecurity',
  'OnlineBackup',
  'DeviceProtection',
  'TechSupport',
  'StreamingTV',
  'StreamingMovies',
  'Contract',
  'PaperlessBilling',
  'PaymentMethod',
  'MonthlyCharges',
  'TotalCharges',
];

const CATEGORICAL_RULES = {
  gender: ['Female', 'Male'],
  SeniorCitizen: ['0', '1', 0, 1],
  Partner: ['Yes', 'No'],
  Dependents: ['Yes', 'No'],
  PhoneService: ['Yes', 'No'],
  MultipleLines: ['No phone service', 'No', 'Yes'],
  InternetService: ['DSL', 'Fiber optic', 'No'],
  OnlineSecurity: ['No internet service', 'No', 'Yes'],
  OnlineBackup: ['No internet service', 'No', 'Yes'],
  DeviceProtection: ['No internet service', 'No', 'Yes'],
  TechSupport: ['No internet service', 'No', 'Yes'],
  StreamingTV: ['No internet service', 'No', 'Yes'],
  StreamingMovies: ['No internet service', 'No', 'Yes'],
  Contract: ['Month-to-month', 'One year', 'Two year'],
  PaperlessBilling: ['Yes', 'No'],
  PaymentMethod: [
    'Electronic check',
    'Mailed check',
    'Bank transfer (automatic)',
    'Credit card (automatic)',
  ],
};

/**
 * Validates parsed CSV data against model expectations.
 * @param {string[]} headers Array of header column names from CSV
 * @param {object[]} rawRows Array of raw row objects
 * @returns {{ valid: boolean, errors: string[], validatedRows: object[] }}
 */
export function validateCsvData(headers, rawRows) {
  const errors = [];

  if (!headers || headers.length === 0) {
    return { valid: false, errors: ['CSV file is empty or missing headers.'], validatedRows: [] };
  }

  // 1. Check for missing required columns
  const headerSet = new Set(headers.map((h) => h.trim()));
  const missingCols = REQUIRED_MODEL_COLUMNS.filter((col) => !headerSet.has(col));

  if (missingCols.length > 0) {
    errors.push(`Missing required feature columns: ${missingCols.join(', ')}`);
    return { valid: false, errors, validatedRows: [] };
  }

  if (!rawRows || rawRows.length === 0) {
    return { valid: false, errors: ['CSV contains no customer data rows.'], validatedRows: [] };
  }

  // 2. Validate row by row
  const validatedRows = [];
  const maxReportedErrors = 5;

  rawRows.forEach((row, idx) => {
    const rowNum = idx + 2; // header is row 1
    const rowErrors = [];

    // Categorical checks
    Object.entries(CATEGORICAL_RULES).forEach(([field, allowed]) => {
      const val = row[field];
      if (val === undefined || val === null || val === '') {
        rowErrors.push(`Row ${rowNum}: "${field}" is required.`);
      } else if (!allowed.includes(val) && !allowed.includes(String(val).trim())) {
        rowErrors.push(
          `Row ${rowNum}: Invalid value "${val}" for "${field}". Expected one of: ${allowed.join(', ')}`
        );
      }
    });

    // Tenure check (int >= 0)
    const tenureNum = Number(row.tenure);
    if (isNaN(tenureNum) || !Number.isInteger(tenureNum) || tenureNum < 0) {
      rowErrors.push(`Row ${rowNum}: "tenure" must be a non-negative integer (received "${row.tenure}").`);
    }

    // MonthlyCharges check (float >= 0)
    const monthlyNum = Number(row.MonthlyCharges);
    if (isNaN(monthlyNum) || monthlyNum < 0) {
      rowErrors.push(`Row ${rowNum}: "MonthlyCharges" must be a positive number (received "${row.MonthlyCharges}").`);
    }

    // TotalCharges check (float >= 0 or empty)
    let totalNum = null;
    if (row.TotalCharges !== undefined && row.TotalCharges !== null && String(row.TotalCharges).trim() !== '') {
      totalNum = Number(row.TotalCharges);
      if (isNaN(totalNum) || totalNum < 0) {
        rowErrors.push(`Row ${rowNum}: "TotalCharges" must be a positive number or empty.`);
      }
    }

    if (rowErrors.length > 0) {
      if (errors.length < maxReportedErrors) {
        errors.push(...rowErrors.slice(0, maxReportedErrors - errors.length));
      }
    } else {
      // Build clean record
      const id = row.customerID || row.customerId || row.customer_id || `CUST-${String(idx + 1).padStart(3, '0')}`;
      const cleanFeatures = {
        gender: row.gender,
        SeniorCitizen: Number(row.SeniorCitizen),
        Partner: row.Partner,
        Dependents: row.Dependents,
        tenure: tenureNum,
        PhoneService: row.PhoneService,
        MultipleLines: row.MultipleLines,
        InternetService: row.InternetService,
        OnlineSecurity: row.OnlineSecurity,
        OnlineBackup: row.OnlineBackup,
        DeviceProtection: row.DeviceProtection,
        TechSupport: row.TechSupport,
        StreamingTV: row.StreamingTV,
        StreamingMovies: row.StreamingMovies,
        Contract: row.Contract,
        PaperlessBilling: row.PaperlessBilling,
        PaymentMethod: row.PaymentMethod,
        MonthlyCharges: monthlyNum,
        TotalCharges: totalNum !== null ? totalNum : monthlyNum * tenureNum,
      };

      validatedRows.push({
        id,
        features: cleanFeatures,
        raw: row,
      });
    }
  });

  if (errors.length > 0) {
    return { valid: false, errors, validatedRows: [] };
  }

  return { valid: true, errors: [], validatedRows };
}

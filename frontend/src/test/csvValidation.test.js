import { describe, it, expect } from 'vitest';
import { validateCsvData, REQUIRED_MODEL_COLUMNS } from '../utils/csvValidation';

function createValidRow(overrides = {}) {
  return {
    customerID: 'CUST-001',
    gender: 'Female',
    SeniorCitizen: '0',
    Partner: 'Yes',
    Dependents: 'No',
    tenure: '12',
    PhoneService: 'Yes',
    MultipleLines: 'No',
    InternetService: 'DSL',
    OnlineSecurity: 'Yes',
    OnlineBackup: 'No',
    DeviceProtection: 'Yes',
    TechSupport: 'No',
    StreamingTV: 'No',
    StreamingMovies: 'No',
    Contract: 'One year',
    PaperlessBilling: 'No',
    PaymentMethod: 'Bank transfer (automatic)',
    MonthlyCharges: '45.20',
    TotalCharges: '542.40',
    ...overrides,
  };
}

describe('validateCsvData', () => {
  const fullHeaders = ['customerID', ...REQUIRED_MODEL_COLUMNS];

  it('validates a complete, valid customer row successfully', () => {
    const row = createValidRow();
    const result = validateCsvData(fullHeaders, [row]);

    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
    expect(result.validatedRows).toHaveLength(1);

    const validated = result.validatedRows[0];
    expect(validated.id).toBe('CUST-001');
    expect(validated.features.gender).toBe('Female');
    expect(validated.features.SeniorCitizen).toBe(0);
    expect(validated.features.tenure).toBe(12);
    expect(validated.features.MonthlyCharges).toBe(45.2);
    expect(validated.features.TotalCharges).toBe(542.4);
  });

  it('rejects empty headers or missing header array', () => {
    const res1 = validateCsvData([], [createValidRow()]);
    expect(res1.valid).toBe(false);
    expect(res1.errors[0]).toMatch(/empty or missing headers/i);

    const res2 = validateCsvData(null, [createValidRow()]);
    expect(res2.valid).toBe(false);
  });

  it('detects missing required feature columns', () => {
    // Missing 'Contract' and 'MonthlyCharges'
    const partialHeaders = fullHeaders.filter((h) => h !== 'Contract' && h !== 'MonthlyCharges');
    const result = validateCsvData(partialHeaders, [createValidRow()]);

    expect(result.valid).toBe(false);
    expect(result.errors[0]).toContain('Missing required feature columns');
    expect(result.errors[0]).toContain('Contract');
    expect(result.errors[0]).toContain('MonthlyCharges');
  });

  it('rejects CSV with headers but no data rows', () => {
    const result = validateCsvData(fullHeaders, []);
    expect(result.valid).toBe(false);
    expect(result.errors[0]).toMatch(/contains no customer data rows/i);
  });

  it('rejects invalid categorical values', () => {
    const invalidRow = createValidRow({
      gender: 'Unknown',
      Contract: 'Lifetime',
      InternetService: 'Satellite',
      PaymentMethod: 'Bitcoin',
    });

    const result = validateCsvData(fullHeaders, [invalidRow]);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('Invalid value "Unknown" for "gender"'))).toBe(true);
    expect(result.errors.some((e) => e.includes('Invalid value "Lifetime" for "Contract"'))).toBe(true);
  });

  it('rejects missing or empty required categorical fields', () => {
    const invalidRow = createValidRow({
      Partner: '',
      OnlineSecurity: null,
    });

    const result = validateCsvData(fullHeaders, [invalidRow]);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('"Partner" is required'))).toBe(true);
  });

  it('validates tenure as non-negative integer and rejects decimals or negatives', () => {
    const rowDec = createValidRow({ tenure: '12.5' });
    const resDec = validateCsvData(fullHeaders, [rowDec]);
    expect(resDec.valid).toBe(false);
    expect(resDec.errors[0]).toContain('tenure');

    const rowNeg = createValidRow({ tenure: '-5' });
    const resNeg = validateCsvData(fullHeaders, [rowNeg]);
    expect(resNeg.valid).toBe(false);
    expect(resNeg.errors[0]).toContain('tenure');

    const rowAlpha = createValidRow({ tenure: 'two_years' });
    const resAlpha = validateCsvData(fullHeaders, [rowAlpha]);
    expect(resAlpha.valid).toBe(false);
    expect(resAlpha.errors[0]).toContain('tenure');

    // 0 tenure is valid
    const rowZero = createValidRow({ tenure: '0', TotalCharges: '0' });
    const resZero = validateCsvData(fullHeaders, [rowZero]);
    expect(resZero.valid).toBe(true);
    expect(resZero.validatedRows[0].features.tenure).toBe(0);
  });

  it('accepts exact decimal monetary charges (e.g. 139.7, 70.35, 0)', () => {
    const rowDec = createValidRow({
      MonthlyCharges: '70.35',
      TotalCharges: '139.70',
    });
    const result = validateCsvData(fullHeaders, [rowDec]);

    expect(result.valid).toBe(true);
    expect(result.validatedRows[0].features.MonthlyCharges).toBe(70.35);
    expect(result.validatedRows[0].features.TotalCharges).toBe(139.7);
  });

  it('rejects negative or non-numeric monetary charges', () => {
    const rowNeg = createValidRow({ MonthlyCharges: '-15.50' });
    const resNeg = validateCsvData(fullHeaders, [rowNeg]);
    expect(resNeg.valid).toBe(false);
    expect(resNeg.errors[0]).toContain('MonthlyCharges');

    const rowNan = createValidRow({ TotalCharges: 'free' });
    const resNan = validateCsvData(fullHeaders, [rowNan]);
    expect(resNan.valid).toBe(false);
    expect(resNan.errors[0]).toContain('TotalCharges');
  });

  it('computes TotalCharges automatically when omitted or empty', () => {
    const rowEmptyTotal = createValidRow({
      tenure: '10',
      MonthlyCharges: '50.00',
      TotalCharges: '',
    });
    const result = validateCsvData(fullHeaders, [rowEmptyTotal]);

    expect(result.valid).toBe(true);
    // Calculated as monthlyNum * tenureNum = 50.00 * 10 = 500
    expect(result.validatedRows[0].features.TotalCharges).toBe(500);
  });

  it('generates fallback IDs when customerID column is absent', () => {
    const row = createValidRow();
    delete row.customerID;
    const result = validateCsvData(REQUIRED_MODEL_COLUMNS, [row]);

    expect(result.valid).toBe(true);
    expect(result.validatedRows[0].id).toBe('CUST-001');
  });
});

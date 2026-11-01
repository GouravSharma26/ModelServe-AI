import { describe, it, expect } from 'vitest';
import { parseCsv } from '../utils/csvParser';

describe('parseCsv utility', () => {
  it('returns empty headers and rows for empty or null inputs', () => {
    expect(parseCsv('')).toEqual({ headers: [], rows: [] });
    expect(parseCsv(null)).toEqual({ headers: [], rows: [] });
    expect(parseCsv(undefined)).toEqual({ headers: [], rows: [] });
    expect(parseCsv('   \n\r  ')).toEqual({ headers: [], rows: [] });
  });

  it('parses valid CSV with headers and rows correctly', () => {
    const csv = `gender,SeniorCitizen,Partner,MonthlyCharges\nMale,0,Yes,70.35\nFemale,1,No,89.50`;
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['gender', 'SeniorCitizen', 'Partner', 'MonthlyCharges']);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({
      gender: 'Male',
      SeniorCitizen: '0',
      Partner: 'Yes',
      MonthlyCharges: '70.35',
    });
    expect(rows[1]).toEqual({
      gender: 'Female',
      SeniorCitizen: '1',
      Partner: 'No',
      MonthlyCharges: '89.50',
    });
  });

  it('handles CRLF (\\r\\n) and mixed line endings', () => {
    const csv = "colA,colB\r\nval1,val2\rval3,val4\nval5,val6";
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['colA', 'colB']);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toEqual({ colA: 'val1', colB: 'val2' });
    expect(rows[1]).toEqual({ colA: 'val3', colB: 'val4' });
    expect(rows[2]).toEqual({ colA: 'val5', colB: 'val6' });
  });

  it('handles quoted values with embedded commas and whitespace', () => {
    const csv = `id,name,payment\n1,"Doe, John","Credit card (automatic)"\n2,"Smith, Jane, Jr.","Bank transfer (automatic)"`;
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['id', 'name', 'payment']);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({
      id: '1',
      name: 'Doe, John',
      payment: 'Credit card (automatic)',
    });
    expect(rows[1]).toEqual({
      id: '2',
      name: 'Smith, Jane, Jr.',
      payment: 'Bank transfer (automatic)',
    });
  });

  it('handles escaped double quotes within quoted values', () => {
    const csv = `id,description\n101,"Customer said ""Do not call"""`;
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['id', 'description']);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({
      id: '101',
      description: 'Customer said "Do not call"',
    });
  });

  it('handles CSV with headers only and no data rows', () => {
    const csv = 'gender,SeniorCitizen,tenure';
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['gender', 'SeniorCitizen', 'tenure']);
    expect(rows).toEqual([]);
  });

  it('handles malformed rows with missing trailing values gracefully', () => {
    const csv = `col1,col2,col3\nval1,val2\nval4,val5,val6,val7`;
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['col1', 'col2', 'col3']);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({ col1: 'val1', col2: 'val2', col3: '' });
    expect(rows[1]).toEqual({ col1: 'val4', col2: 'val5', col3: 'val6' });
  });

  it('parses multiple customer records accurately', () => {
    const lines = ['customerID,tenure,MonthlyCharges,TotalCharges'];
    for (let i = 1; i <= 25; i++) {
      lines.push(`CUST-${i},${i},${(20.5 + i).toFixed(2)},${(100.0 + i * 20).toFixed(2)}`);
    }
    const csv = lines.join('\n');
    const { headers, rows } = parseCsv(csv);

    expect(headers).toEqual(['customerID', 'tenure', 'MonthlyCharges', 'TotalCharges']);
    expect(rows).toHaveLength(25);
    expect(rows[0].customerID).toBe('CUST-1');
    expect(rows[24].customerID).toBe('CUST-25');
  });
});


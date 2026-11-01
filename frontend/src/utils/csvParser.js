/**
 * Lightweight, robust CSV parser for browser environments.
 * Handles quoted fields containing commas and carriage return line breaks.
 */
export function parseCsv(csvText) {
  if (!csvText || typeof csvText !== 'string') {
    return { headers: [], rows: [] };
  }

  const lines = splitLines(csvText.trim());
  if (lines.length === 0) {
    return { headers: [], rows: [] };
  }

  const rawHeaders = parseCsvLine(lines[0]);
  const headers = rawHeaders.map((h) => h.trim());

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    const values = parseCsvLine(line);
    const rowObj = {};
    headers.forEach((header, idx) => {
      rowObj[header] = values[idx] !== undefined ? values[idx].trim() : '';
    });
    rows.push(rowObj);
  }

  return { headers, rows };
}

/**
 * Split text by CRLF or LF, respecting quoted multiline strings if any.
 */
function splitLines(text) {
  const lines = [];
  let currentLine = '';
  let insideQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      insideQuotes = !insideQuotes;
      currentLine += char;
    } else if (!insideQuotes && (char === '\r' && nextChar === '\n')) {
      lines.push(currentLine);
      currentLine = '';
      i++; // skip \n
    } else if (!insideQuotes && (char === '\n' || char === '\r')) {
      lines.push(currentLine);
      currentLine = '';
    } else {
      currentLine += char;
    }
  }

  if (currentLine.length > 0) {
    lines.push(currentLine);
  }

  return lines;
}

/**
 * Parse a single CSV line into an array of string values.
 */
function parseCsvLine(line) {
  const result = [];
  let currentVal = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        currentVal += '"';
        i++; // skip escaped quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(currentVal);
      currentVal = '';
    } else {
      currentVal += char;
    }
  }

  result.push(currentVal);
  return result;
}

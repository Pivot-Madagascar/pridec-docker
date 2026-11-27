// The value check of pivot_dhis_tools (check_import_value), as GET /pipeline/imports/fetched passes it on:
// text  = "numNA: 0 | minimum value: 1 | maximum value: 164 | negative values: 0 | number of values: 148"
// error = "Potential errors in data to be imported: 1 orgUnits exceed case threshold of 100; 2 negative values. <text>"
// ponytail: reads the library's wording; another wording shows the raw text (null / [error]), check_dhis_value.py.

export interface CheckStats {
  min: string
  max: string
  missing: string
  negative: string
}

const KEYS: Record<string, keyof CheckStats> = {
  numNA: 'missing', 'minimum value': 'min', 'maximum value': 'max', 'negative values': 'negative'
}

/** The check's numbers, or null when `text` is not in the expected form. "number of values" is left out: rows says it. */
export function parseCheckStats(text: string | null): CheckStats | null {
  const stats: Partial<CheckStats> = {}
  for (const part of (text ?? '').split(' | ')) {
    const [key, value] = part.split(': ')
    if (key in KEYS && value !== undefined) stats[KEYS[key]] = value
  }
  return Object.keys(stats).length === 4 ? (stats as CheckStats) : null
}

/** The problems of a flagged element, without the summary repeated after them. */
export function checkProblems(error: string | null): string[] {
  if (!error) return []
  const match = /^Potential errors in data to be imported: (.*?)\. numNA:/.exec(error)
  return match ? match[1].split('; ') : [error]
}

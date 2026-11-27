import type { CsvPreviewData } from '@/types/inputs'

/**
 * Incremental RFC 4180 parser: push() text in any chunk sizes, rows come out through onRow.
 * State survives chunk boundaries, so quotes and CRLF split across chunks are fine.
 */
export function createCsvParser(onRow: (row: string[]) => void) {
  let field = ''
  let row: string[] = []
  let inQuotes = false
  let quoteSeen = false // a '"' inside quotes: escaped quote or closing quote, decided by the next char
  let skipLf = false

  const endRow = () => {
    row.push(field)
    if (row.length > 1 || row[0] !== '') onRow(row) // skip blank lines
    field = ''
    row = []
  }

  const push = (text: string) => {
    for (let i = 0; i < text.length; i++) {
      const ch = text[i]
      if (skipLf) {
        skipLf = false
        if (ch === '\n') continue
      }
      if (inQuotes) {
        if (quoteSeen) {
          quoteSeen = false
          if (ch === '"') {
            field += '"'
            continue
          }
          inQuotes = false // closing quote: handle ch as an unquoted char below
        } else {
          if (ch === '"') quoteSeen = true
          else field += ch
          continue
        }
      }
      if (ch === '"' && field === '') inQuotes = true
      else if (ch === ',') {
        row.push(field)
        field = ''
      } else if (ch === '\n') endRow()
      else if (ch === '\r') {
        endRow()
        skipLf = true
      } else field += ch
    }
  }

  const end = () => {
    if (field !== '' || row.length > 0) endRow()
  }

  return { push, end }
}

/** One pass over the stream: keeps the first `limit` rows, summarises all of them (same shape as etlhub). */
export async function previewCsvStream(stream: ReadableStream<Uint8Array>, limit: number): Promise<CsvPreviewData> {
  const preview: CsvPreviewData = { columns: [], rows: [], total_rows: 0, period_range: null, org_units: 0 }
  const orgUnits = new Set<string>()
  let orgIndex = -1
  let periodIndex = -1
  let header = true

  const parser = createCsvParser(row => {
    if (header) {
      header = false
      preview.columns = row.map(column => column.trim())
      orgIndex = preview.columns.indexOf('orgUnit')
      periodIndex = preview.columns.indexOf('period')
      return
    }
    preview.total_rows++
    if (preview.rows.length < limit) preview.rows.push(row)
    if (orgIndex >= 0 && row[orgIndex] !== undefined) orgUnits.add(row[orgIndex])
    const period = periodIndex >= 0 ? row[periodIndex] : ''
    if (period) {
      // YYYYMM strings: lexical order is chronological order.
      const [first, last] = preview.period_range ?? [period, period]
      preview.period_range = [period < first ? period : first, period > last ? period : last]
    }
  })

  // TextDecoderStream drops the UTF-8 BOM and keeps multi-byte chars split across chunks intact.
  const reader = stream.pipeThrough(new TextDecoderStream()).getReader()
  for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) parser.push(chunk.value)
  parser.end()

  preview.org_units = orgUnits.size
  return preview
}

/** '202504' → 'Apr 2025' (locale dependent). Anything that is not YYYYMM is returned unchanged. */
export function formatPeriod(value: string): string {
  const match = /^(\d{4})(\d{2})$/.exec(value)
  const month = match ? Number(match[2]) : 0
  if (!match || month < 1 || month > 12) return value
  return new Date(Number(match[1]), month - 1, 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
}

/** Rounds decimals to 3 places for display; integers, codes and text stay as they are. */
export function formatCell(value: string): string {
  return /^-?\d+\.\d{4,}$/.test(value) ? Number(value).toFixed(3) : value
}

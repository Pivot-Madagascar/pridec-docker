import { describe, it, expect } from 'vitest'
import { createCsvParser, previewCsvStream, formatPeriod, formatCell } from '@/utils/preview'

const parseAll = (...chunks: string[]) => {
  const rows: string[][] = []
  const parser = createCsvParser(row => rows.push(row))
  chunks.forEach(parser.push)
  parser.end()
  return rows
}

const streamOf = (...chunks: string[]) => {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach(c => controller.enqueue(encoder.encode(c)))
      controller.close()
    }
  })
}

describe('createCsvParser', () => {
  it('handles quotes, escaped quotes, commas and newlines inside quotes', () => {
    expect(parseAll('a,"b, c","say ""hi""","l1\nl2"\n')).toEqual([['a', 'b, c', 'say "hi"', 'l1\nl2']])
  })

  it('handles CRLF, empty fields, blank lines and a missing final newline', () => {
    expect(parseAll('a,,c\r\n\r\n"",x')).toEqual([['a', '', 'c'], ['', 'x']])
  })

  it('gives the same rows whatever the chunk boundaries', () => {
    const text = '"orgUnit","period"\r\n"A ""1""",202401\r\nB,202402\n'
    const whole = parseAll(text)
    for (let i = 1; i < text.length; i++) {
      expect(parseAll(text.slice(0, i), text.slice(i))).toEqual(whole)
    }
  })
})

describe('previewCsvStream', () => {
  it('keeps the first rows and summarises the whole stream', async () => {
    const lines = ['"orgUnit","period",x']
    for (let i = 0; i < 150; i++) lines.push(`"OU${i % 3}","2024${String((i % 12) + 1).padStart(2, '0')}",${i}`)
    const text = '﻿' + lines.join('\n') + '\n'

    const preview = await previewCsvStream(streamOf(text.slice(0, 50), text.slice(50, 51), text.slice(51)), 100)

    expect(preview.columns).toEqual(['orgUnit', 'period', 'x'])
    expect(preview.rows).toHaveLength(100)
    expect(preview.rows[0]).toEqual(['OU0', '202401', '0'])
    expect(preview.total_rows).toBe(150)
    expect(preview.period_range).toEqual(['202401', '202412'])
    expect(preview.org_units).toBe(3)
  })

  it('works without orgUnit or period columns', async () => {
    const preview = await previewCsvStream(streamOf('a,b\n1,2\n'), 100)

    expect(preview).toEqual({ columns: ['a', 'b'], rows: [['1', '2']], total_rows: 1, period_range: null, org_units: 0 })
  })
})

describe('formatPeriod', () => {
  it('turns YYYYMM into a readable month', () => {
    expect(formatPeriod('202504')).toMatch(/2025/)
    expect(formatPeriod('202504')).not.toBe('202504')
  })

  it('returns anything else unchanged', () => {
    expect(formatPeriod('2025-04')).toBe('2025-04')
    expect(formatPeriod('202513')).toBe('202513')
  })
})

describe('formatCell', () => {
  it('rounds long decimals and keeps integers, codes and text as they are', () => {
    expect(formatCell('0.123456789012345')).toBe('0.123')
    expect(formatCell('29')).toBe('29')
    expect(formatCell('202401')).toBe('202401')
    expect(formatCell('Site, north')).toBe('Site, north')
    expect(formatCell('')).toBe('')
  })
})

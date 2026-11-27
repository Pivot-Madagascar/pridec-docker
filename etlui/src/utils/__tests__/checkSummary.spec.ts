import { describe, it, expect } from 'vitest'
import { checkProblems, parseCheckStats } from '@/utils/checkSummary'

const TEXT = 'numNA: 0 | minimum value: 1 | maximum value: 164 | negative values: 2 | number of values: 148'

describe('parseCheckStats', () => {
  it('reads the numbers of the check summary', () => {
    expect(parseCheckStats(TEXT)).toEqual({ min: '1', max: '164', missing: '0', negative: '2' })
  })

  it('returns null for another wording, so the raw text is shown', () => {
    expect(parseCheckStats('all good')).toBeNull()
    expect(parseCheckStats(null)).toBeNull()
  })
})

describe('checkProblems', () => {
  it('lists the problems without the summary repeated after them', () => {
    const error = `Potential errors in data to be imported: 1 orgUnits exceed case threshold of 100; 2 negative values. ${TEXT}`
    expect(checkProblems(error)).toEqual(['1 orgUnits exceed case threshold of 100', '2 negative values'])
  })

  it('keeps any other error whole', () => {
    expect(checkProblems('data is empty')).toEqual(['data is empty'])
    expect(checkProblems(null)).toEqual([])
  })
})

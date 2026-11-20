import { describe, it, expect } from 'vitest'
import { useActivityLog } from '@/composables/useActivityLog'

describe('useActivityLog', () => {
  it('keeps only the 5 most recent entries, newest first', () => {
    const { activityLog, addActivity } = useActivityLog()
    for (let i = 1; i <= 7; i++) addActivity(`a${i}`, 'Accepted', true)
    expect(activityLog.value.map(e => e.action)).toEqual(['a7', 'a6', 'a5', 'a4', 'a3'])
  })
})

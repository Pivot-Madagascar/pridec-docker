import { describe, it, expect } from 'vitest'
import { statusColor } from '@/utils/status'

describe('statusColor', () => {
  it('colours HTTP codes and job statuses alike', () => {
    expect([202, 'success', 409, 500, 'error', 'running', 'pending', null].map(statusColor)).toEqual([
      'bg-green-900 text-green-300', 'bg-green-900 text-green-300', 'bg-yellow-900 text-yellow-300',
      'bg-red-900 text-red-300', 'bg-red-900 text-red-300', 'bg-blue-900 text-blue-300', 'bg-blue-900 text-blue-300',
      'bg-gray-700 text-gray-300'
    ])
  })
})

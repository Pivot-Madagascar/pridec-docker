import { describe, it, expect } from 'vitest'
import { statusColor } from '@/utils/status'

describe('statusColor', () => {
  it('colours HTTP codes and job statuses alike', () => {
    expect([202, 'success', 409, 500, 'error', 'running', 'pending', null].map(statusColor)).toEqual([
      'bg-success/15 text-success', 'bg-success/15 text-success', 'bg-warning/15 text-warning',
      'bg-destructive/15 text-destructive', 'bg-destructive/15 text-destructive', 'bg-primary/15 text-primary',
      'bg-primary/15 text-primary', 'bg-muted text-muted-foreground'
    ])
  })
})

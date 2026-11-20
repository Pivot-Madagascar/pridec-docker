import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { Progress } from '@/components/ui/progress'

describe('Progress', () => {
  it('fills the share of max, not of 100', () => {
    const bar = mount(Progress, { props: { modelValue: 3, max: 9 } })
    expect(bar.find('[data-slot="progress-indicator"]').attributes('style')).toContain('translateX(-66.66')
  })
})

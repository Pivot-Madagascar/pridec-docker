import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const login = vi.fn().mockResolvedValue(undefined)
vi.mock('@/services/auth', () => ({
  login: (...args: unknown[]) => login(...args),
  getDhis2Urls: vi.fn().mockResolvedValue([])
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ replace: vi.fn() }) }))

import LoginForm from '@/views/Auth/LoginForm.vue'

describe('LoginForm', () => {
  it('sends what the user typed in the shadcn inputs', async () => {
    const wrapper = mount(LoginForm)
    await wrapper.find('#dhis2Url').setValue(' https://dhis2.example ')
    await wrapper.find('#username').setValue('admin')
    await wrapper.find('#password').setValue('secret')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(login).toHaveBeenCalledWith('https://dhis2.example', 'admin', 'secret')
    expect((wrapper.find('#password').element as HTMLInputElement).value).toBe('') // cleared after the request
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'
import Login from '../components/Login.vue'

// Mock axios
vi.mock('axios', () => ({
  default: {
    post: vi.fn()
  }
}))

const mockAxiosPost = vi.mocked(axios.post)

// Mock vue-router
const mockRouter = {
  push: vi.fn()
}

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal() as any
  return {
    ...actual,
    useRouter: () => mockRouter
  }
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

describe('Login Component', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()

    // Create router instance for component
    const router = createRouter({
      history: createWebHistory(),
      routes: []
    })

    wrapper = mount(Login, {
      global: {
        plugins: [router]
      }
    })
  })

  describe('Component Rendering', () => {
    it('renders the login form correctly', () => {
      expect(wrapper.text()).toContain('Sign in')
      expect(wrapper.text()).toContain('Username')
      expect(wrapper.text()).toContain('Password')
      expect(wrapper.text()).toContain('Create your account')
    })

    it('renders all form inputs', () => {
      const inputs = wrapper.findAll('input')
      expect(inputs).toHaveLength(2)

      const usernameInput = inputs[0]
      const passwordInput = inputs[1]

      expect(usernameInput.attributes('type')).toBe('text')
      expect(usernameInput.attributes('placeholder')).toBe('Enter your username')
      expect(passwordInput.attributes('type')).toBe('password')
      expect(passwordInput.attributes('placeholder')).toBe('Enter your password')
    })

    it('renders submit button', () => {
      const button = wrapper.find('button[type="submit"]')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('Sign in')
    })

    it('renders register link', () => {
      const link = wrapper.findComponent({ name: 'RouterLink' })
      expect(link.exists()).toBe(true)
      expect(link.props('to')).toBe('/register')
      expect(link.text()).toBe('Create your account')
    })

    it('renders dark mode toggle button', () => {
      const darkModeButton = wrapper.find('button')
      expect(darkModeButton.text()).toContain('Dark Mode')
    })

    it('renders environment indicator', () => {
      expect(wrapper.text()).toContain('Environment: Development')
    })
  })

  describe('Form Data Binding', () => {
    it('binds username input to reactive data', async () => {
      const usernameInput = wrapper.find('input[type="text"]')
      await usernameInput.setValue('testuser')

      expect(wrapper.vm.username).toBe('testuser')
    })

    it('binds password input to reactive data', async () => {
      const passwordInput = wrapper.find('input[type="password"]')
      await passwordInput.setValue('testpass')

      expect(wrapper.vm.password).toBe('testpass')
    })
  })

  describe('Dark Mode Toggle', () => {
    it('toggles dark mode when button is clicked', async () => {
      const darkModeButton = wrapper.find('button')
      const initialDarkMode = wrapper.vm.isDarkMode

      await darkModeButton.trigger('click')

      expect(wrapper.vm.isDarkMode).toBe(!initialDarkMode)
    })

    it('updates button text when dark mode is toggled', async () => {
      const darkModeButton = wrapper.find('button')

      // Initially shows "Dark Mode"
      expect(darkModeButton.text()).toContain('Dark Mode')

      // Click to enable dark mode
      await darkModeButton.trigger('click')
      expect(darkModeButton.text()).toContain('Light Mode')

      // Click again to disable dark mode
      await darkModeButton.trigger('click')
      expect(darkModeButton.text()).toContain('Dark Mode')
    })

    it('toggles document class when dark mode is toggled', async () => {
      const toggleDarkMode = vi.spyOn(document.documentElement.classList, 'toggle')

      const darkModeButton = wrapper.find('button')
      await darkModeButton.trigger('click')

      expect(toggleDarkMode).toHaveBeenCalledWith('dark', true)
    })
  })

  describe('Form Submission', () => {
    it('submits form when required fields are filled', async () => {
      const form = wrapper.find('form')

      // Fill required fields
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('testpass')

      // Mock axios to prevent actual API call
      mockAxiosPost.mockResolvedValue({ data: { access_token: 'test' } })

      await form.trigger('submit')

      // Verify axios was called
      expect(mockAxiosPost).toHaveBeenCalledWith('/api/auth/login', {
        username: 'testuser',
        password: 'testpass'
      })
    })

    it('shows loading state during submission', async () => {
      // Mock successful login with delay
      mockAxiosPost.mockImplementation(() => new Promise(resolve =>
        setTimeout(() => resolve({ data: { access_token: 'test-token' } }), 10)
      ))

      const form = wrapper.find('form')
      const button = wrapper.find('button[type="submit"]')

      // Submit form
      await form.trigger('submit')
      await wrapper.vm.$nextTick()

      // Check loading state
      expect(wrapper.vm.loading).toBe(true)
      expect(button.text()).toBe('Signing in...')

      // Wait for completion
      await new Promise(resolve => setTimeout(resolve, 20))

      expect(wrapper.vm.loading).toBe(false)
      expect(button.text()).toBe('Sign in')
    })

    it('handles successful login', async () => {
      const testToken = 'test-jwt-token'
      mockAxiosPost.mockResolvedValue({
        data: { access_token: testToken }
      })

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('testpass')

      // Submit
      await form.trigger('submit')

      // Verify API call
      expect(mockAxiosPost).toHaveBeenCalledWith('/api/auth/login', {
        username: 'testuser',
        password: 'testpass'
      })

      // Verify token storage
      expect(localStorage.setItem).toHaveBeenCalledWith('token', testToken)

      // Verify navigation
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard')
    })

    it('handles login failure', async () => {
      mockAxiosPost.mockRejectedValue(new Error('Invalid credentials'))

      const form = wrapper.find('form')

      // Submit form
      await form.trigger('submit')

      // Check error display
      expect(wrapper.vm.error).toBe('Invalid credentials')
      expect(wrapper.text()).toContain('Invalid credentials')

      // Verify no navigation occurred
      expect(mockRouter.push).not.toHaveBeenCalled()
    })

    it('clears previous errors on new submission', async () => {
      // Set initial error
      wrapper.vm.error = 'Previous error'

      // Mock successful login
      mockAxiosPost.mockResolvedValue({
        data: { access_token: 'test-token' }
      })

      const form = wrapper.find('form')
      await form.trigger('submit')

      expect(wrapper.vm.error).toBe('')
    })

    it('handles network errors gracefully', async () => {
      mockAxiosPost.mockRejectedValue(new Error('Network Error'))

      const form = wrapper.find('form')
      await form.trigger('submit')

      expect(wrapper.vm.error).toBe('Invalid credentials')
    })

    it('handles API response without access_token', async () => {
      mockAxiosPost.mockResolvedValue({
        data: { message: 'Login successful' }
      })

      const form = wrapper.find('form')
      await form.trigger('submit')

      expect(wrapper.vm.error).toBe('Invalid credentials')
      expect(mockRouter.push).not.toHaveBeenCalled()
    })
  })

  describe('Form Validation', () => {
    it('requires username field', () => {
      const usernameInput = wrapper.find('input[type="text"]')
      expect(usernameInput.attributes('required')).toBeDefined()
    })

    it('requires password field', () => {
      const passwordInput = wrapper.find('input[type="password"]')
      expect(passwordInput.attributes('required')).toBeDefined()
    })

    it('disables submit button during loading', async () => {
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button[type="submit"]')
      expect(button.attributes('disabled')).toBeDefined()
    })
  })

  describe('Accessibility', () => {
    it('has proper labels for inputs', () => {
      const labels = wrapper.findAll('label')
      expect(labels).toHaveLength(2)
      expect(labels[0].text()).toBe('Username')
      expect(labels[1].text()).toBe('Password')
    })

    it('has proper form structure', () => {
      const form = wrapper.find('form')
      expect(form.exists()).toBe(true)

      const inputs = form.findAll('input')
      const labels = form.findAll('label')
      const button = form.find('button[type="submit"]')

      expect(inputs).toHaveLength(2)
      expect(labels).toHaveLength(2)
      expect(button.exists()).toBe(true)
    })
  })

  describe('Styling', () => {
    it('applies correct CSS classes for form styling', () => {
      const form = wrapper.find('form')
      expect(form.classes()).toContain('space-y-4')

      const inputs = wrapper.findAll('input')
      inputs.forEach(input => {
        expect(input.classes()).toContain('w-full')
        expect(input.classes()).toContain('px-3')
        expect(input.classes()).toContain('py-2')
        expect(input.classes()).toContain('border')
        expect(input.classes()).toContain('rounded')
      })
    })

    it('applies Amazon-inspired color scheme', () => {
      const header = wrapper.find('header')
      expect(header.classes()).toContain('bg-amazon-dark')

      const button = wrapper.find('button[type="submit"]')
      expect(button.classes()).toContain('bg-amazon-orange')
    })
  })

  describe('Error Handling', () => {
    it('displays error messages when login fails', async () => {
      mockAxiosPost.mockRejectedValue(new Error('Login failed'))

      const form = wrapper.find('form')
      await form.trigger('submit')

      const errorElement = wrapper.find('.text-red-600')
      expect(errorElement.exists()).toBe(true)
      expect(errorElement.text()).toBe('Invalid credentials')
    })

    it('hides error messages on successful login', async () => {
      // First show an error
      wrapper.vm.error = 'Previous error'
      await wrapper.vm.$nextTick()

      let errorElement = wrapper.find('.text-red-600')
      expect(errorElement.exists()).toBe(true)

      // Then successful login
      mockAxiosPost.mockResolvedValue({
        data: { access_token: 'test-token' }
      })

      const form = wrapper.find('form')
      await form.trigger('submit')

      await wrapper.vm.$nextTick()

      errorElement = wrapper.find('.text-red-600')
      expect(errorElement.exists()).toBe(false)
    })
  })
})
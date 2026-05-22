import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'
import Register from '../components/Register.vue'

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

// Mock lucide-vue-next
vi.mock('lucide-vue-next', () => ({
  Database: {
    template: '<div>Database Icon</div>'
  }
}))

describe('Register Component', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()

    // Create router instance for component
    const router = createRouter({
      history: createWebHistory(),
      routes: []
    })

    wrapper = mount(Register, {
      global: {
        plugins: [router]
      }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Component Rendering', () => {
    it('renders the registration form correctly', () => {
      expect(wrapper.text()).toContain('Create your account')
      expect(wrapper.text()).toContain('ETL Dashboard')
      expect(wrapper.text()).toContain('Already have an account?')
      expect(wrapper.text()).toContain('Sign in')
    })

    it('renders all form inputs', () => {
      const inputs = wrapper.findAll('input')
      expect(inputs).toHaveLength(4)

      const usernameInput = wrapper.find('#username')
      const emailInput = wrapper.find('#email')
      const passwordInput = wrapper.find('#password')
      const confirmPasswordInput = wrapper.find('#confirmPassword')

      expect(usernameInput.exists()).toBe(true)
      expect(emailInput.exists()).toBe(true)
      expect(passwordInput.exists()).toBe(true)
      expect(confirmPasswordInput.exists()).toBe(true)
    })

    it('renders submit button', () => {
      const button = wrapper.find('button[type="submit"]')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('Create Account')
    })

    it('renders login link', () => {
      const link = wrapper.findComponent({ name: 'RouterLink' })
      expect(link.exists()).toBe(true)
      expect(link.props('to')).toBe('/login')
      expect(link.text()).toBe('Sign in')
    })

    it('renders Database icon', () => {
      expect(wrapper.text()).toContain('Database Icon')
    })
  })

  describe('Form Data Binding', () => {
    it('binds username input to reactive data', async () => {
      const usernameInput = wrapper.find('#username')
      await usernameInput.setValue('testuser')

      expect(wrapper.vm.username).toBe('testuser')
    })

    it('binds email input to reactive data', async () => {
      const emailInput = wrapper.find('#email')
      await emailInput.setValue('test@example.com')

      expect(wrapper.vm.email).toBe('test@example.com')
    })

    it('binds password input to reactive data', async () => {
      const passwordInput = wrapper.find('#password')
      await passwordInput.setValue('testpass')

      expect(wrapper.vm.password).toBe('testpass')
    })

    it('binds confirm password input to reactive data', async () => {
      const confirmPasswordInput = wrapper.find('#confirmPassword')
      await confirmPasswordInput.setValue('testpass')

      expect(wrapper.vm.confirmPassword).toBe('testpass')
    })
  })

  describe('Form Validation', () => {
    it('requires username field', () => {
      const usernameInput = wrapper.find('#username')
      expect(usernameInput.attributes('required')).toBeDefined()
    })

    it('requires email field', () => {
      const emailInput = wrapper.find('#email')
      expect(emailInput.attributes('required')).toBeDefined()
      expect(emailInput.attributes('type')).toBe('email')
    })

    it('requires password field with minimum length', () => {
      const passwordInput = wrapper.find('#password')
      expect(passwordInput.attributes('required')).toBeDefined()
      expect(passwordInput.attributes('minlength')).toBe('6')
    })

    it('requires confirm password field with minimum length', () => {
      const confirmPasswordInput = wrapper.find('#confirmPassword')
      expect(confirmPasswordInput.attributes('required')).toBeDefined()
      expect(confirmPasswordInput.attributes('minlength')).toBe('6')
    })

    it('validates password confirmation', async () => {
      const form = wrapper.find('form')

      // Fill form with mismatched passwords
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('different123')

      // Submit form
      await form.trigger('submit')

      // Check error message
      expect(wrapper.vm.error).toBe('Passwords do not match')
      expect(wrapper.text()).toContain('Passwords do not match')

      // Verify API was not called
      expect(mockAxiosPost).not.toHaveBeenCalled()
    })
  })

  describe('Form Submission', () => {
    it('submits form when required fields are filled', async () => {
      const form = wrapper.find('form')

      // Fill required fields
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Mock axios to prevent actual API call
      mockAxiosPost.mockResolvedValue({})

      await form.trigger('submit')

      // Verify axios was called
      expect(mockAxiosPost).toHaveBeenCalledWith('/api/auth/register', {
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com'
      })
    })


    it('handles successful registration', async () => {
      mockAxiosPost.mockResolvedValue({})

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Submit
      await form.trigger('submit')

      // Verify API call
      expect(mockAxiosPost).toHaveBeenCalledWith('/api/auth/register', {
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com'
      })

      // Verify success message
      expect(wrapper.vm.success).toBe('Account created successfully. Redirecting to login...')
      expect(wrapper.text()).toContain('Account created successfully')

      // Verify navigation after timeout
      vi.advanceTimersByTime(1200)
      expect(mockRouter.push).toHaveBeenCalledWith('/login')
    })

    it('handles registration failure with API error', async () => {
      const errorMessage = 'Username already exists'
      mockAxiosPost.mockRejectedValue({
        response: {
          data: { detail: errorMessage }
        }
      })

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('#username').setValue('existinguser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Submit
      await form.trigger('submit')

      // Check error display
      expect(wrapper.vm.error).toBe(errorMessage)
      expect(wrapper.text()).toContain(errorMessage)

      // Verify no navigation occurred
      expect(mockRouter.push).not.toHaveBeenCalled()
    })

    it('handles registration failure without API error details', async () => {
      mockAxiosPost.mockRejectedValue(new Error('Network error'))

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Submit
      await form.trigger('submit')

      // Check generic error message
      expect(wrapper.vm.error).toBe('Registration failed')
    })

    it('clears previous errors on new submission', async () => {
      // Set initial error
      wrapper.vm.error = 'Previous error'

      // Mock successful registration
      mockAxiosPost.mockResolvedValue({})

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Submit
      await form.trigger('submit')

      expect(wrapper.vm.error).toBe('')
    })

    it('clears previous success messages on new submission', async () => {
      // Set initial success
      wrapper.vm.success = 'Previous success'

      // Mock failed registration
      mockAxiosPost.mockRejectedValue(new Error('Error'))

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Submit
      await form.trigger('submit')

      expect(wrapper.vm.success).toBe('')
    })
  })

  describe('Form Button State', () => {
    it('disables submit button during loading', async () => {
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button[type="submit"]')
      expect(button.attributes('disabled')).toBeDefined()
    })

    it('enables submit button when not loading', () => {
      const button = wrapper.find('button[type="submit"]')
      expect(button.attributes('disabled')).toBeUndefined()
    })
  })

  describe('Error and Success Messages', () => {
    it('displays error messages in red alert box', async () => {
      wrapper.vm.error = 'Test error message'
      await wrapper.vm.$nextTick()

      const errorDiv = wrapper.find('.bg-red-900\\/30')
      expect(errorDiv.exists()).toBe(true)
      expect(errorDiv.text()).toContain('Test error message')
    })

    it('displays success messages in green alert box', async () => {
      wrapper.vm.success = 'Test success message'
      await wrapper.vm.$nextTick()

      const successDiv = wrapper.find('.bg-green-900\\/30')
      expect(successDiv.exists()).toBe(true)
      expect(successDiv.text()).toContain('Test success message')
    })

    it('hides error messages when success is shown', async () => {
      wrapper.vm.error = 'Error message'
      wrapper.vm.success = 'Success message'
      await wrapper.vm.$nextTick()

      const errorDiv = wrapper.find('.bg-red-900\\/30')
      const successDiv = wrapper.find('.bg-green-900\\/30')

      expect(errorDiv.exists()).toBe(true)
      expect(successDiv.exists()).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has proper labels for all inputs', () => {
      const labels = wrapper.findAll('label')
      expect(labels).toHaveLength(4)

      const labelTexts = labels.map(label => label.text())
      expect(labelTexts).toContain('Username')
      expect(labelTexts).toContain('Email')
      expect(labelTexts).toContain('Password')
      expect(labelTexts).toContain('Confirm Password')
    })

    it('has proper form structure', () => {
      const form = wrapper.find('form')
      expect(form.exists()).toBe(true)

      const inputs = form.findAll('input')
      const labels = form.findAll('label')
      const button = form.find('button[type="submit"]')

      expect(inputs).toHaveLength(4)
      expect(labels).toHaveLength(4)
      expect(button.exists()).toBe(true)
    })

    it('has proper autocomplete attributes', () => {
      const usernameInput = wrapper.find('#username')
      const emailInput = wrapper.find('#email')
      const passwordInput = wrapper.find('#password')
      const confirmPasswordInput = wrapper.find('#confirmPassword')

      expect(usernameInput.attributes('autocomplete')).toBe('username')
      expect(emailInput.attributes('autocomplete')).toBe('email')
      expect(passwordInput.attributes('autocomplete')).toBe('new-password')
      expect(confirmPasswordInput.attributes('autocomplete')).toBe('new-password')
    })
  })

  describe('Navigation', () => {
    it('navigates to login page after successful registration', async () => {
      mockAxiosPost.mockResolvedValue({})

      const form = wrapper.find('form')

      // Fill form
      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#email').setValue('test@example.com')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('#confirmPassword').setValue('password123')

      // Submit
      await form.trigger('submit')

      // Fast-forward timer
      vi.advanceTimersByTime(1200)

      expect(mockRouter.push).toHaveBeenCalledWith('/login')
    })

    it('provides link to login page', () => {
      const link = wrapper.findComponent({ name: 'RouterLink' })
      expect(link.props('to')).toBe('/login')
    })
  })
})
import { describe, it, expect } from 'vitest'

import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import App from '../App.vue'

describe('App', () => {
  it('mounts renders properly', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/dashboard',
          name: 'Dashboard',
          component: { template: '<div>Dashboard</div>' },
          meta: { title: 'Dashboard' }
        }
      ]
    })

    const wrapper = mount(App, {
      global: {
        plugins: [router]
      }
    })

    expect(wrapper.text()).toContain('PRIDE-C ETL')
  })
})

import { beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { config } from '@vue/test-utils'
import { defineComponent } from 'vue'

// shadcn dialogs render through a portal (<Teleport to="body">): keep their content inside the mounted wrapper.
config.global.stubs = { teleport: defineComponent({ setup: (_, { slots }) => () => slots.default?.() }) }

beforeEach(() => {
  setActivePinia(createPinia())
})

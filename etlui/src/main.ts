import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/base.css'

// ponytail: follows the OS only; the header toggle of D3 (tailwind-migration.md) overrides it when added
const darkOs = matchMedia('(prefers-color-scheme: dark)')
const applyTheme = () => document.documentElement.classList.toggle('dark', darkOs.matches)
applyTheme()
darkOs.addEventListener('change', applyTheme)

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
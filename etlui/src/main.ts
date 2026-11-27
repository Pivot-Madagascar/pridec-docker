import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/base.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// After the first route is known: App shows the menu or not from its meta (Login has none).
router.isReady().then(() => app.mount('#app'))
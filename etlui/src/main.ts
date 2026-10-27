import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/base.css'

// ponytail: dark only while the hand-written surfaces are still dark hex (shadcn-migration lots 3-5);
// lot 6 follows the OS and adds the header toggle (D3)
document.documentElement.classList.add('dark')

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
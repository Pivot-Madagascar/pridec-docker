<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getDhis2Urls, login } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const dhis2Url = ref(import.meta.env.VITE_DHIS2_URL || '')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const dhis2Urls = ref<string[]>([])
getDhis2Urls().then(urls => (dhis2Urls.value = urls))

watch(
  () => authStore.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      router.replace({ name: 'Dashboard' })
    }
  },
  { immediate: true }
)

const handleSubmit = async () => {
    error.value = ''
    if (!dhis2Url.value.trim() || !username.value.trim() || !password.value) {
        error.value = 'Please fill in the DHIS2 URL, username and password'
        return
    }
    loading.value = true
    try {
        await login(dhis2Url.value.trim(), username.value.trim(), password.value)
    } catch (e: any) {
        error.value = e?.message || 'Login failed'
    } finally {
        // Never keep the password in memory longer than the request.
        password.value = ''
        loading.value = false
    }
}
</script>

<template>
  <div class="login-container">
    <form class="login-card" @submit.prevent="handleSubmit">
      <h2 class="form-title">Login with DHIS2</h2>
      <div v-if="error" class="error-message">{{ error }}</div>
      <p class="login-description">
        Use your account on the target DHIS2 instance.
      </p>
      <div class="form-group">
        <label for="dhis2Url">DHIS2 URL</label>
        <input
          id="dhis2Url"
          v-model="dhis2Url"
          type="url"
          autocomplete="url"
          list="dhis2-urls"
          placeholder="https://your-dhis2-instance.org"
          required
        />
        <datalist id="dhis2-urls">
          <option v-for="url in dhis2Urls" :key="url" :value="url" />
        </datalist>
      </div>
      <div class="form-group">
        <label for="username">Username</label>
        <input
          id="username"
          v-model="username"
          type="text"
          autocomplete="username"
          required
        />
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>
      <button type="submit" class="submit-btn" :disabled="loading">
        {{ loading ? 'Logging in...' : 'Login' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  color: white;
}

.login-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 2rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.form-title {
  margin-bottom: 1rem;
}

.login-description {
  color: #666;
  margin-bottom: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  text-align: left;
}

.form-group label {
  font-weight: 500;
}

.form-group input {
   padding: 0.5rem;
   border: 1px solid #ccc;
   border-radius: 4px;
   font-size: 1rem;
}

.error-message {
  background: #fee;
  color: #c00;
  padding: 0.5rem;
  border-radius: 4px;
  text-align: center;
}

.submit-btn {
  padding: 0.75rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.submit-btn:hover {
  background: #2563eb;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { handleTokenSubmit } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const token = ref('')
const dhis2Url = ref(import.meta.env.VITE_DHIS2_URL || '')
const error = ref('')

watch(
  () => authStore.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      router.replace({ name: 'Landing' })
    }
  },
  { immediate: true }
)

const handleSubmit = async () => {
    error.value = ''
    if (!token.value.trim()) {
        error.value = 'Please enter a token'
        return
    }
    try {
        await handleTokenSubmit(token.value, dhis2Url.value)
    } catch (e) {
        error.value = 'Invalid DHIS2 token'
    }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="form-title">Login with DHIS2 Token</h2>
      <div v-if="error" class="error-message">{{ error }}</div>
      <p class="login-description">
        Paste your DHIS2 Bearer token below to authenticate.
      </p>
      <div class="form-group">
        <label for="dhis2Url">DHIS2 URL</label>
        <input 
          id="dhis2Url" 
          v-model="dhis2Url" 
          type="url"
          placeholder="https://your-dhis2-instance.org"
        />
      </div>
      <div class="form-group">
        <label for="token">DHIS2 Token</label>
        <textarea 
          id="token" 
          v-model="token" 
          placeholder="Paste your DHIS2 Bearer token here"
          rows="3"
          required
        ></textarea>
      </div>
      <button @click="handleSubmit" class="submit-btn">
        Login
      </button>
    </div>
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

.form-group textarea {
   padding: 0.5rem;
   border: 1px solid #ccc;
   border-radius: 4px;
   font-family: monospace;
   resize: vertical;
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
</style>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getDhis2Urls, login } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

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
    <Card class="w-full max-w-100 px-8">
    <form class="login-form" @submit.prevent="handleSubmit">
      <h2 class="form-title">Login with DHIS2</h2>
      <div v-if="error" class="error-message">{{ error }}</div>
      <p class="login-description">
        Use your account on the target DHIS2 instance.
      </p>
      <div class="form-group">
        <Label for="dhis2Url">DHIS2 URL</Label>
        <Input
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
        <Label for="username">Username</Label>
        <Input
          id="username"
          v-model="username"
          type="text"
          autocomplete="username"
          required
        />
      </div>
      <div class="form-group">
        <Label for="password">Password</Label>
        <Input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>
      <Button type="submit" size="lg" :disabled="loading">
        {{ loading ? 'Logging in...' : 'Login' }}
      </Button>
    </form>
    </Card>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  color: var(--foreground);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  text-align: center;
}

.form-title {
  margin-bottom: 1rem;
}

.login-description {
  color: var(--muted-foreground);
  margin-bottom: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  text-align: left;
}

.error-message {
  background: color-mix(in oklab, var(--destructive) 15%, transparent);
  color: var(--destructive);
  padding: 0.5rem;
  border-radius: 4px;
  text-align: center;
}
</style>
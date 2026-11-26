<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CircleHelp, Database, Globe, KeyRound, LoaderCircle, User } from '@lucide/vue'
import { getDhis2Urls, login } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/ThemeToggle.vue'
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
  <!-- The page alone (no menu): a soft primary glow behind a centred card. -->
  <div class="relative flex min-h-svh flex-col items-center justify-center gap-6 bg-background px-4 py-10 text-foreground">
    <div aria-hidden="true" class="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--color-primary)_0%,transparent_60%)] opacity-15" />
    <div class="absolute top-4 right-4"><ThemeToggle /></div>

    <!-- Same brand as the side menu. -->
    <div class="relative flex items-center gap-3">
      <span class="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md">
        <Database class="size-6" />
      </span>
      <span class="grid leading-tight">
        <span class="text-xl font-semibold">ETL Hub</span>
        <span class="text-sm text-muted-foreground">PRIDE-C Data Platform</span>
      </span>
    </div>

    <Card class="relative w-full max-w-md gap-0 p-8 shadow-lg">
      <form class="flex flex-col gap-5" @submit.prevent="handleSubmit">
        <div class="space-y-1 text-center">
          <h2 class="text-2xl font-semibold tracking-tight">Sign in with DHIS2</h2>
          <p class="text-sm text-muted-foreground">Use your account on the target DHIS2 instance.</p>
        </div>

        <div v-if="error" role="alert" class="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{{ error }}</div>

        <div class="grid gap-2">
          <Label for="dhis2Url">DHIS2 URL</Label>
          <div class="relative">
            <Globe class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="dhis2Url"
              v-model="dhis2Url"
              type="url"
              autocomplete="url"
              list="dhis2-urls"
              placeholder="https://your-dhis2-instance.org"
              class="pl-9"
              required
            />
          </div>
          <datalist id="dhis2-urls">
            <option v-for="url in dhis2Urls" :key="url" :value="url" />
          </datalist>
        </div>
        <div class="grid gap-2">
          <Label for="username">Username</Label>
          <div class="relative">
            <User class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input id="username" v-model="username" type="text" autocomplete="username" class="pl-9" required />
          </div>
        </div>
        <div class="grid gap-2">
          <Label for="password">Password</Label>
          <div class="relative">
            <KeyRound class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input id="password" v-model="password" type="password" autocomplete="current-password" class="pl-9" required />
          </div>
        </div>

        <Button type="submit" size="lg" class="w-full" :disabled="loading">
          <LoaderCircle v-if="loading" class="animate-spin" />
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </Button>
      </form>
    </Card>

    <router-link to="/help" class="relative inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:underline" data-test="login-help-link">
      <CircleHelp class="size-4" />
      New here? Read how the application works
    </router-link>
  </div>
</template>

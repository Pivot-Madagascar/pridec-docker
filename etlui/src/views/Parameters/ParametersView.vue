<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Item, ItemContent, ItemDescription, ItemTitle } from '@/components/ui/item'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LOG_LEVELS } from '@/types/config'

// One section at a time, chosen in the side menu and kept in the URL (?section=); /admin/config lands on configuration.
const SECTIONS = [
  { id: 'profile', label: 'Profile' },
  { id: 'dhis2', label: 'DHIS2' },
  { id: 'configuration', label: 'Configuration' },
  { id: 'gee', label: 'GEE variables' }
]
const route = useRoute()
const router = useRouter()
const section = computed({
  get: () => SECTIONS.find(s => s.id === route.query.section)?.id ?? 'profile',
  set: id => void router.replace({ query: { section: id } })
})

const auth = useAuthStore()
const configStore = useConfigStore()
// DHIS2 URL and token come from the login and are read-only here.
const tokenStatus = computed(() => {
  const config = configStore.config
  if (!config?.has_dhis_token) return 'No active token: log in again'
  if (!config.dhis_token_expires_at) return 'Active'
  return `Active until ${new Date(config.dhis_token_expires_at * 1000).toLocaleString()}`
})
// Read only here since 2026-11-25: DISEASE_CODE and OU_LEVEL come from each run, the others from .env (Reload from .env).
const form = ref({ parent_ou: '', log_level: '', pivot_url: '' })
const showSuccess = ref(false)

// etlhub copies these values from .env into Redis at each start: a change here lasts until the next restart.
const fillForm = () => {
  const config = configStore.config
  if (!config) return
  form.value = {
    parent_ou: config.parent_ou || '',
    log_level: config.log_level || '',
    pivot_url: config.pivot_url || ''
  }
}

onMounted(async () => {
  await configStore.fetchConfig()
  fillForm()
})

const flashSuccess = () => {
  if (configStore.error) return
  showSuccess.value = true
  setTimeout(() => (showSuccess.value = false), 3000)
}

const handleReload = async () => {
  if (!window.confirm('This will overwrite all current values with those from .env. Continue?')) return
  await configStore.reloadConfig()
  fillForm()
  flashSuccess()
}

const profile = computed(() => [
  ['Username', auth.user?.username],
  ['Display name', auth.user?.displayName],
  ['Email', auth.user?.email],
  ['ID', auth.user?.id]
])
</script>

<template>
  <div class="parameters">
    <!-- Page header (shadcn Item). -->
    <Item class="p-0" data-test="page-header">
      <ItemContent>
        <ItemTitle><h2 class="text-2xl font-bold">Parameters</h2></ItemTitle>
        <ItemDescription class="line-clamp-none">Your DHIS2 profile and session, then etlhub's configuration and GEE variables.</ItemDescription>
      </ItemContent>
    </Item>
    <!-- Side menu as vertical tabs (reka: arrow keys move between them); stacked above the section on narrow screens. -->
    <Tabs v-model="section" orientation="vertical" class="gap-6 md:flex-row md:items-start">
      <TabsList data-test="parameters-menu" aria-label="Parameters sections"
        class="h-auto w-full shrink-0 flex-row flex-wrap items-stretch justify-start gap-1 p-1 md:w-48 md:flex-col">
        <TabsTrigger v-for="s in SECTIONS" :key="s.id" :value="s.id" class="h-auto flex-none justify-start px-3 py-2">
          {{ s.label }}
        </TabsTrigger>
      </TabsList>

      <div class="min-w-0 flex-1">
        <TabsContent value="profile">
          <Card class="section">
            <header>
              <h3 class="section-title">Profile</h3>
              <p class="hint">Your DHIS2 user, from the login.</p>
            </header>
            <dl v-if="auth.user" class="details">
              <div v-for="[label, value] in profile" :key="label" class="detail">
                <dt>{{ label }}</dt>
                <dd>{{ value || 'N/A' }}</dd>
              </div>
            </dl>
          </Card>
        </TabsContent>

        <TabsContent value="dhis2">
          <Card class="section">
            <header>
              <h3 class="section-title">DHIS2</h3>
              <p class="hint">The DHIS2 you logged in to, read only: log in again to change it.</p>
            </header>
            <dl class="details">
              <div class="detail"><dt>URL</dt><dd>{{ configStore.config?.dhis_url || 'N/A' }}</dd></div>
              <div class="detail"><dt>Token</dt><dd>{{ tokenStatus }}</dd></div>
            </dl>
          </Card>
        </TabsContent>

        <TabsContent value="configuration">
          <Card class="section">
            <header>
              <h3 class="section-title">Configuration</h3>
              <p class="hint">Read only: etlhub takes these values from .env at each start. To change one, edit .env, then Reload from .env. Shared by test and production mode.</p>
            </header>
            <div v-if="configStore.error" class="error-message">{{ configStore.error }}</div>
            <div v-if="showSuccess" class="success-message">Reloaded from .env</div>

            <div class="fields">
              <div class="form-group">
                <Label for="parent_ou">Parent OrgUnit ID</Label>
                <Input id="parent_ou" v-model="form.parent_ou" type="text" disabled placeholder="Not set" />
              </div>
              <div class="form-group">
                <Label for="log_level">Log level</Label>
                <!-- Reka refuses '' as an item value: 'default' stands for no LOG_LEVEL (etlhub's INFO). -->
                <Select :model-value="form.log_level || 'default'" disabled @update:model-value="v => (form.log_level = v === 'default' ? '' : String(v))">
                  <SelectTrigger id="log_level" class="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Default (INFO)</SelectItem>
                    <SelectItem v-for="level in LOG_LEVELS" :key="level" :value="level">{{ level }}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="form-group sm:col-span-2">
                <Label for="pivot_url">Pivot URL</Label>
                <Input id="pivot_url" v-model="form.pivot_url" type="url" disabled placeholder="Not set" />
                <!-- PIVOT_TOKEN stays in etlhub's .env: only whether it is set comes to the browser. -->
                <p class="hint" data-test="pivot-token">
                  {{ configStore.config?.has_pivot_token ? 'Set in etlhub (.env)' : 'Missing: set PIVOT_TOKEN in etlhub\'s .env' }}
                </p>
              </div>
            </div>

            <div class="button-group">
              <Button variant="secondary" :disabled="configStore.loading" @click="handleReload">
                {{ configStore.loading ? 'Loading...' : 'Reload from .env' }}
              </Button>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="gee">
          <!-- Read only, from pridec_gee: each pass chooses its own on Home when it starts. -->
          <Card class="section" data-test="gee-variables">
            <header>
              <h3 class="section-title">GEE variables available</h3>
              <p class="hint">From pridec_gee. Each pass chooses its own on Home, when it starts.</p>
            </header>
            <ul class="list-inside list-disc font-mono text-xs text-muted-foreground">
              <li v-for="name in configStore.config?.gee_variables ?? []" :key="name">{{ name }}</li>
            </ul>
          </Card>
        </TabsContent>
      </div>
    </Tabs>
  </div>
</template>

<style scoped>
@reference "../../styles/base.css";

.parameters {
  @apply space-y-6 text-foreground;
}

.section {
  @apply gap-5 p-6;
}

.section-title {
  @apply text-lg font-semibold;
}

.hint {
  @apply text-xs text-muted-foreground;
}

/* Label left, value right, one line each (as the Journal's pass details). */
.details {
  @apply divide-y text-sm;
}

.detail {
  @apply flex items-center justify-between gap-4 py-2;
}

.detail dt {
  @apply text-muted-foreground;
}

.detail dd {
  @apply min-w-0 truncate font-mono;
}

.fields {
  @apply grid gap-4 sm:grid-cols-2;
}

.form-group {
  @apply flex flex-col gap-2;
}

.error-message {
  @apply rounded-lg bg-destructive/15 p-3 text-sm text-destructive;
}

.success-message {
  @apply rounded-lg bg-success/15 p-3 text-sm text-success;
}

.button-group {
  @apply flex justify-end gap-3;
}
</style>

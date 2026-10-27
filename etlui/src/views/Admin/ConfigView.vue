<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { Button } from '@/components/ui/button'
import { LOG_LEVELS, type ConfigUpdate } from '@/types/config'

const configStore = useConfigStore()
// DHIS2 URL and token come from the login and are read-only here.
const tokenStatus = computed(() => {
  const config = configStore.config
  if (!config?.has_dhis_token) return 'No active token: log in again'
  if (!config.dhis_token_expires_at) return 'Active'
  return `Active until ${new Date(config.dhis_token_expires_at * 1000).toLocaleString()}`
})
const form = ref({
  parent_ou: '',
  ou_level: '' as number | string | null,
  disease_code: '',
  log_level: '',
  gee_variables: ''
})
const showSuccess = ref(false)

// etlhub copies these values from .env into Redis at each start: a change here lasts until the next restart.
const fillForm = () => {
  const config = configStore.config
  if (!config) return
  form.value = {
    parent_ou: config.parent_ou || '',
    ou_level: config.ou_level ?? '',
    disease_code: config.disease_code || '',
    log_level: config.log_level || '',
    gee_variables: config.gee_variables || ''
  }
}

onMounted(async () => {
  await configStore.fetchConfig()
  fillForm()
})

const handleSave = async () => {
  showSuccess.value = false
  const payload = {
    parent_ou: form.value.parent_ou || null,
    ou_level: form.value.ou_level ? Number(form.value.ou_level) : null,
    disease_code: form.value.disease_code || null,
    log_level: (form.value.log_level || null) as ConfigUpdate['log_level'],
    // '' is sent as is: it means all GEE variables
    gee_variables: form.value.gee_variables.trim()
  }
  await configStore.updateConfig(payload)
  flashSuccess()
}

const flashSuccess = () => {
  if (configStore.error) return
  showSuccess.value = true
  setTimeout(() => showSuccess.value = false, 3000)
}

const handleReload = async () => {
  if (!window.confirm('This will overwrite all current values with those from .env. Continue?')) {
    return
  }
  await configStore.reloadConfig()
  fillForm()
  flashSuccess()
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="form-title">Dynamic Configuration</h2>
      
      <div v-if="configStore.error" class="error-message">
        {{ configStore.error }}
      </div>
      
      <div v-if="showSuccess" class="success-message">
        Saved successfully
      </div>

      <div class="form-group">
        <label for="dhis_url">DHIS URL (from login)</label>
        <input
          id="dhis_url"
          :value="configStore.config?.dhis_url || ''"
          type="url"
          readonly
        />
      </div>

      <div class="form-group">
        <label>DHIS Token</label>
        <p class="token-status">{{ tokenStatus }}</p>
      </div>

      <div class="form-group">
        <label for="parent_ou">Parent OrgUnit ID</label>
        <input
          id="parent_ou"
          v-model="form.parent_ou"
          type="text"
          placeholder="OrgUnit ID (e.g., VtP4BdCeXIo)"
        />
      </div>

      <div class="form-group">
        <label for="ou_level">OrgUnit Level</label>
        <input
          id="ou_level"
          v-model.number="form.ou_level"
          type="number"
          min="1"
          max="10"
          placeholder="5 for CSB, 6 for fokontany"
        />
      </div>

      <div class="form-group">
        <label for="disease_code">Disease Code</label>
        <input
          id="disease_code"
          v-model="form.disease_code"
          type="text"
          placeholder="pridec_historic_CSBMalaria"
        />
      </div>

      <div class="form-group">
        <label for="log_level">Log level</label>
        <select id="log_level" v-model="form.log_level">
          <option value="">Default (INFO)</option>
          <option v-for="level in LOG_LEVELS" :key="level" :value="level">{{ level }}</option>
        </select>
      </div>

      <div class="form-group">
        <label for="gee_variables">GEE variables</label>
        <input
          id="gee_variables"
          v-model="form.gee_variables"
          type="text"
          pattern="[A-Za-z0-9_]+( *, *[A-Za-z0-9_]+)*"
          placeholder="Empty = all variables (comma-separated names)"
        />
      </div>

      <p class="hint">Values are reset from .env each time etlhub starts.</p>

      <div class="button-group">
        <Button class="flex-1" @click="handleSave" :disabled="configStore.loading">
          {{ configStore.loading ? 'Saving...' : 'Save' }}
        </Button>
        <Button variant="secondary" class="flex-1" @click="handleReload" :disabled="configStore.loading">
          {{ configStore.loading ? 'Loading...' : 'Reload from .env' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";

.login-container {
  @apply flex justify-center items-center min-h-[60vh] text-white;
}

.login-card {
  @apply flex flex-col gap-4 p-8 border border-white/10 rounded-xl bg-[#0f172a] max-w-md w-full;
}

.form-title {
  @apply text-2xl font-bold text-white mb-2;
}

.form-group {
  @apply flex flex-col gap-2 text-left;
}

.form-group label {
  @apply block text-sm font-medium text-white;
}

.form-group input,
.form-group select {
  @apply w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors;
}

.form-group input[readonly] {
  @apply opacity-60 cursor-not-allowed;
}

.hint {
  @apply text-xs text-gray-400;
}

.token-status {
  @apply text-sm text-gray-300;
}

.error-message {
  @apply bg-red-900/30 text-red-300 p-3 rounded-lg text-sm;
}

.success-message {
  @apply bg-green-900/30 text-green-300 p-3 rounded-lg text-sm;
}

.button-group {
  @apply flex gap-3 mt-4;
}
</style>
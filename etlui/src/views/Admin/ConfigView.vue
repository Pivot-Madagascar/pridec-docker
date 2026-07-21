<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()
const form = ref({
  dhis_url: '',
  dhis_token: '',
  parent_ou: '',
  ou_level: '' as number | string | null,
  disease_code: ''
})
const showSuccess = ref(false)

onMounted(async () => {
  await configStore.fetchConfig()
  if (configStore.config) {
    form.value = {
      dhis_url: configStore.config.dhis_url || '',
      dhis_token: configStore.config.dhis_token || '',
      parent_ou: configStore.config.parent_ou || '',
      ou_level: configStore.config.ou_level ?? '',
      disease_code: configStore.config.disease_code || ''
    }
  }
})

const handleSave = async () => {
  showSuccess.value = false
  const payload = {
    dhis_url: form.value.dhis_url || null,
    dhis_token: form.value.dhis_token || null,
    parent_ou: form.value.parent_ou || null,
    ou_level: form.value.ou_level ? Number(form.value.ou_level) : null,
    disease_code: form.value.disease_code || null
  }
  try {
    await configStore.updateConfig(payload)
    showSuccess.value = true
    setTimeout(() => showSuccess.value = false, 3000)
  } catch (e) {
    console.error('Failed to update config:', e)
  }
}

const handleReload = async () => {
  if (!window.confirm('This will overwrite all current values with those from .env. Continue?')) {
    return
  }
  try {
    await configStore.reloadConfig()
    if (configStore.config) {
      form.value = {
        dhis_url: configStore.config.dhis_url || '',
        dhis_token: configStore.config.dhis_token || '',
        parent_ou: configStore.config.parent_ou || '',
        ou_level: configStore.config.ou_level ?? '',
        disease_code: configStore.config.disease_code || ''
      }
    }
    showSuccess.value = true
    setTimeout(() => showSuccess.value = false, 3000)
  } catch (e) {
    console.error('Failed to reload config:', e)
  }
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
        <label for="dhis_url">DHIS URL</label>
        <input
          id="dhis_url"
          v-model="form.dhis_url"
          type="url"
          placeholder="https://your-dhis2-instance.org"
        />
      </div>

      <div class="form-group">
        <label for="dhis_token">DHIS Token</label>
        <input
          id="dhis_token"
          v-model="form.dhis_token"
          type="password"
          placeholder="Bearer token"
        />
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

      <div class="button-group">
        <button @click="handleSave" :disabled="configStore.loading" class="submit-btn">
          {{ configStore.loading ? 'Saving...' : 'Save' }}
        </button>
        <button @click="handleReload" :disabled="configStore.loading" class="reload-btn">
          {{ configStore.loading ? 'Loading...' : 'Reload from .env' }}
        </button>
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

.form-group input {
  @apply w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors;
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

.submit-btn {
  @apply flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}

.reload-btn {
  @apply flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}
</style>
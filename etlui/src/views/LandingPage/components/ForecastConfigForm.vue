<template>
  <div class="config-form">
    <div class="form-fields">
      <div class="form-field">
        <label class="field-label" for="disease-select">Maladie</label>
        <select
          id="disease-select"
          v-model="disease"
          class="field-select"
        >
          <option value="">Sélectionner une maladie</option>
          <option value="Malaria">Malaria</option>
          <option value="Diarrhea">Diarrhea</option>
          <option value="Respinf">Respinf</option>
        </select>
      </div>

      <div class="form-field">
        <label class="field-label" for="data-source-select">Source de données</label>
        <select
          id="data-source-select"
          v-model="dataSource"
          class="field-select"
        >
          <option value="">Sélectionner une source</option>
          <option value="ADJ">ADJ</option>
          <option value="COM">COM</option>
          <option value="CSB">CSB</option>
        </select>
      </div>

      <div class="form-field">
        <label class="field-label" for="ou-level">OrgUnit Level</label>
        <input
          id="ou-level"
          type="text"
          :value="ouLevel"
          readonly
          class="field-input readonly"
        />
      </div>

      <div class="form-field">
        <label class="field-label">Mode test</label>
        <div class="toggle-group">
          <button
            type="button"
            :class="['toggle-btn', { active: test === 'NON' }]"
            @click="setTestValue('NON')"
          >
            NON
          </button>
          <button
            type="button"
            :class="['toggle-btn', { active: test === 'OUI' }]"
            @click="setTestValue('OUI')"
          >
            OUI
          </button>
        </div>
      </div>

      <div class="form-field">
        <label class="field-label" for="forecast-start">Date de début prévision</label>
        <input
          id="forecast-start"
          type="text"
          :value="forecastStart"
          readonly
          class="field-input readonly"
        />
      </div>

      <div v-if="dataSource === 'CSB'" class="form-field">
        <label class="field-label" for="alert-name">Nom d'alerte</label>
        <input
          id="alert-name"
          type="text"
          :value="alertName"
          readonly
          class="field-input readonly"
        />
      </div>

      <div class="form-field">
        <label class="field-label" for="disease-code">Code maladie final</label>
        <input
          id="disease-code"
          type="text"
          :value="diseaseCode"
          readonly
          class="field-input readonly"
        />
      </div>
    </div>

    <div class="form-summary">
      <h4 class="summary-title">Résumé de la configuration</h4>
      <div class="summary-grid">
        <div class="summary-item">
          <span class="summary-label">Maladie</span>
          <span class="summary-value">{{ disease || '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Source de données</span>
          <span class="summary-value">{{ dataSource || '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">OrgUnit Level</span>
          <span class="summary-value">{{ ouLevel || '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Mode test</span>
          <span class="summary-value">{{ test }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Forecast start</span>
          <span class="summary-value">{{ forecastStart }}</span>
        </div>
        <div v-if="dataSource === 'CSB'" class="summary-item">
          <span class="summary-label">Alert name</span>
          <span class="summary-value">{{ alertName || '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Disease code</span>
          <span class="summary-value">{{ diseaseCode || '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useForecastConfigStore } from '@/stores/forecastConfig'

const forecastConfig = useForecastConfigStore()
const {
  disease,
  dataSource,
  test,
  ouLevel,
  forecastStart,
  alertName,
  diseaseCode,
  isValid,
} = storeToRefs(forecastConfig)

const setTestValue = (value: 'OUI' | 'NON') => {
  forecastConfig.setTest(value)
}

defineExpose({ isValid })
</script>

<style scoped>
.config-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.form-fields {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #cbd5e1;
}

.field-select,
.field-input {
  padding: 0.75rem 1rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  color: #f1f5f9;
  font-size: 0.875rem;
  outline: none;
  transition: all 0.2s ease;
}

.field-select:focus,
.field-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

.field-input.readonly {
  cursor: default;
  opacity: 0.7;
}

.field-select option {
  background: #1e293b;
  color: #f1f5f9;
}

.toggle-group {
  display: flex;
  gap: 0.25rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 0.25rem;
}

.toggle-btn {
  flex: 1;
  padding: 0.5rem 1rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  color: #94a3b8;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn.active {
  background: #6366f1;
  color: white;
}

.toggle-btn:hover:not(.active) {
  color: #e2e8f0;
}

.form-summary {
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.summary-title {
  font-size: 1rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 0.375rem;
}

.summary-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.summary-value {
  font-size: 0.75rem;
  font-weight: 500;
  color: #f1f5f9;
}

@media (max-width: 640px) {
  .form-fields {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
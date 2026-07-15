<template>
  <section>
    <h2 class="section-header">ETL Pipeline</h2>
    <div class="grid grid-cols-3-lg gap-4">
      <button
        @click="$emit('trigger-etl', 'import_gee')"
        :disabled="loading.import_gee"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">Import GEE</span>
          <span v-if="loading.import_gee" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.import_gee" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">Google Earth Engine data import</p>
      </button>

      <button
        @click="$emit('trigger-etl', 'import_pivot_com')"
        :disabled="loading.import_pivot_com"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">Import Pivot COM</span>
          <span v-if="loading.import_pivot_com" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.import_pivot_com" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">Community health data</p>
      </button>

      <button
        @click="$emit('trigger-etl', 'import_pivot_csb')"
        :disabled="loading.import_pivot_csb"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">Import Pivot CSB</span>
          <span v-if="loading.import_pivot_csb" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.import_pivot_csb" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">CSB surveillance data</p>
      </button>

      <button
        @click="$emit('trigger-etl', 'build_analytics')"
        :disabled="loading.build_analytics"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">Build Analytics</span>
          <span v-if="loading.build_analytics" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.build_analytics" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">Compute analytics tables</p>
      </button>

      <button
        @click="$emit('trigger-etl', 'calc_csb_alerts')"
        :disabled="loading.calc_csb_alerts"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">CSB Alerts</span>
          <span v-if="loading.calc_csb_alerts" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.calc_csb_alerts" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">Calculate alert thresholds</p>
      </button>

      <button
        @click="$emit('trigger-etl', 'update_key')"
        :disabled="loading.update_key"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">Update Key</span>
          <span v-if="loading.update_key" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.update_key" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">Refresh API keys</p>
      </button>

      <button
        @click="$emit('trigger-etl', 'post_forecast')"
        :disabled="loading.post_forecast"
        class="btn-etl"
      >
        <div class="btn-etl-header">
          <span class="btn-etl-title">Post Forecast</span>
          <span v-if="loading.post_forecast" class="btn-etl-status-running">Running...</span>
          <span v-else-if="results.post_forecast" class="btn-etl-status-done">✓ Done</span>
        </div>
        <p class="btn-etl-description">Submit forecast results</p>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  loading: Record<string, boolean>
  results: Record<string, boolean>
}>()
</script>
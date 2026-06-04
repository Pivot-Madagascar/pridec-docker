<template>
  <section>
    <h2 class="section-header">Quick Actions</h2>
    <div class="grid-cols-2-md gap-4">
      <button
        @click="$emit('run-forecast')"
        class="btn-forecast"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="btn-forecast-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <div class="btn-forecast-text">
          <span class="btn-forecast-text-title">Run Forecast</span>
          <span class="btn-forecast-text-subtitle">Start ML forecasting pipeline</span>
        </div>
      </button>

      <button
        @click="$emit('fetch-climate')"
        :disabled="loadingClimate"
        class="btn-fetch"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="btn-fetch-icon-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        </svg>
        <div class="btn-fetch-text">
          <span class="btn-fetch-text-title">Fetch Climate</span>
          <span class="btn-fetch-text-subtitle" :class="{ 'btn-fetch-text-subtitle-loading': loadingClimate, 'btn-fetch-text-subtitle-default': !loadingClimate }">
            <template v-if="loadingClimate">Fetching...</template>
            <template v-else>Weather & climate data</template>
          </span>
        </div>
      </button>

      <button
        @click="$emit('fetch-disease')"
        :disabled="loadingDisease"
        class="btn-fetch"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="btn-fetch-icon-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
        </svg>
        <div class="btn-fetch-text">
          <span class="btn-fetch-text-title">Fetch Disease</span>
          <span class="btn-fetch-text-subtitle" :class="{ 'btn-fetch-text-subtitle-loading': loadingDisease, 'btn-fetch-text-subtitle-default': !loadingDisease }">
            <template v-if="loadingDisease">Fetching...</template>
            <template v-else>Health data ingestion</template>
          </span>
        </div>
      </button>

      <button
        @click="$emit('fetch-geojson')"
        :disabled="loadingGeoJSON"
        class="btn-fetch"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="btn-fetch-icon-purple" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        <div class="btn-fetch-text">
          <span class="btn-fetch-text-title">Fetch GeoJSON</span>
          <span class="btn-fetch-text-subtitle" :class="{ 'btn-fetch-text-subtitle-loading': loadingGeoJSON, 'btn-fetch-text-subtitle-default': !loadingGeoJSON }">
            <template v-if="loadingGeoJSON">Fetching...</template>
            <template v-else>Geospatial boundaries</template>
          </span>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  loadingClimate: boolean
  loadingDisease: boolean
  loadingGeoJSON: boolean
}>()
</script>
<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col">
    <!-- Header -->
    <header
      class="bg-amazon-dark text-white px-6 py-4 flex justify-between items-center shadow-md"
    >
      <h1 class="text-lg font-bold">PRIDE-C ETL</h1>
      <div class="flex items-center space-x-4">
        <span
          class="bg-amazon-orange text-amazon-dark text-xs font-bold px-2 py-1 rounded"
        >
          Environment: {{ envLabel }}
        </span>
        <button
          @click="toggleDarkMode"
          class="px-3 py-1 bg-amazon-light dark:bg-gray-700 rounded text-sm font-medium"
        >
          {{ isDarkMode ? "Light Mode" : "Dark Mode" }}
        </button>
      </div>
    </header>

    <!-- Content -->
    <main
      class="flex items-center justify-center flex-1 px-4 py-8"
    >
      <div
        class="w-full max-w-md bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 space-y-6"
      >
        <!-- Heading -->
        <div class="text-center">
          <h2 class="text-3xl font-bold text-amazon-dark dark:text-white">
            Welcome to PRIDE-C ETL
          </h2>
          <p class="mt-2 text-gray-600 dark:text-gray-400 text-sm">
            Data ingestion and forecasting platform for malaria surveillance
          </p>
        </div>

        <!-- Actions -->
        <div class="space-y-3">
          <router-link
            to="/data-fetch"
            class="block w-full px-4 py-3 text-center bg-amazon-orange hover:bg-yellow-500 text-amazon-dark font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
          >
            <Download class="w-5 h-5" />
            <span>Fetch Data</span>
          </router-link>

          <router-link
            to="/forecasting"
            class="block w-full px-4 py-3 text-center bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
          >
            <Activity class="w-5 h-5" />
            <span>Run Forecast</span>
          </router-link>
        </div>

        <!-- Divider -->
        <div class="flex items-center space-x-2">
          <div class="flex-1 h-px bg-gray-300 dark:bg-gray-600"></div>
          <span class="text-xs text-gray-500 dark:text-gray-400">More options</span>
          <div class="flex-1 h-px bg-gray-300 dark:bg-gray-600"></div>
        </div>

        <!-- Secondary links -->
        <div class="grid grid-cols-2 gap-3">
          <router-link
            to="/reports"
            class="block px-4 py-2 text-center bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Reports
          </router-link>
          <router-link
            to="/forecast-post"
            class="block px-4 py-2 text-center bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Post Forecast
          </router-link>
          <router-link
            to="/docs"
            class="block px-4 py-2 text-center bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            API Docs
          </router-link>
          <router-link
            to="/login"
            class="block px-4 py-2 text-center bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-lg text-sm font-medium hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
          >
            Log In
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Download, Activity } from 'lucide-vue-next'

const isDarkMode = ref<boolean>(false)
const envLabel = ref<string>('Development')

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value
  localStorage.setItem('dark_mode', String(isDarkMode.value))
  document.documentElement.classList.toggle('dark', isDarkMode.value)
}

onMounted(() => {
  const stored = localStorage.getItem('dark_mode')
  if (stored !== null) {
    isDarkMode.value = stored === 'true'
    if (isDarkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }
})
</script>

<style scoped>
/* Amazon-inspired colors */
:root {
  --amazon-dark: #131921;
  --amazon-orange: #febd69;
  --amazon-light: #f3f3f3;
}
.bg-amazon-dark {
  background-color: var(--amazon-dark);
}
.bg-amazon-orange {
  background-color: var(--amazon-orange);
}
.bg-amazon-light {
  background-color: var(--amazon-light);
}
.text-amazon-dark {
  color: var(--amazon-dark);
}
</style>

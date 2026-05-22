<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center p-4">
    <div class="max-w-lg w-full space-y-8 text-center">
      <!-- Header -->
      <div class="flex items-center justify-center space-x-2 mb-8">
        <Database class="w-12 h-12 text-orange-400" />
        <h1 class="text-3xl font-bold text-white">ETL Dashboard</h1>
      </div>

      <!-- Main Content -->
      <div class="bg-gray-800 rounded-lg border border-gray-700 p-8 space-y-6">
        <!-- 404 Illustration -->
        <div class="relative mx-auto w-64 h-48">
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="text-8xl font-bold text-gray-700">404</div>
          </div>
          <svg class="w-full h-full" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <path d="M30,30 L70,70 M70,30 L30,70" stroke="#F97316" stroke-width="4" stroke-linecap="round"/>
            <circle cx="50" cy="50" r="40" stroke="#4B5563" stroke-width="2" fill="none"/>
          </svg>
        </div>

        <!-- Message -->
        <div class="space-y-2">
          <h2 class="text-2xl font-bold text-white">Page Not Found</h2>
          <p class="text-gray-400">
            Sorry, we couldn't find the page you're looking for. The page may have been moved, deleted, or never existed.
          </p>
        </div>

        <!-- Actions -->
        <div class="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <router-link
            to="/dashboard"
            class="px-5 py-3 bg-orange-400 hover:bg-orange-500 text-gray-900 font-medium rounded-md transition-colors flex items-center justify-center space-x-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span>Go to Dashboard</span>
          </router-link>
          
          <button
            @click="goBack"
            class="px-5 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-md transition-colors flex items-center justify-center space-x-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span>Go Back</span>
          </button>
        </div>
      </div>

      <!-- Support Link -->
      <div class="text-gray-500 text-sm">
        Need help? <a href="#" class="text-orange-400 hover:text-orange-300">Contact support</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Database } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
/* Optional: Add a subtle animation to the 404 graphic */
svg {
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
}

path {
  animation: draw 1.5s ease-in-out forwards;
}

@keyframes draw {
  from {
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
  }
  to {
    stroke-dashoffset: 0;
  }
}
</style>
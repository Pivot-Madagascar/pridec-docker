<template>
  <div class="min-h-screen bg-white dark:bg-gray-950">
    <!-- Top Navbar -->
    <header class="bg-[#131921] text-white px-6 py-4 shadow-lg">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-3 hover:opacity-80 transition-opacity">
          <div class="w-10 h-10 bg-gradient-to-br from-[#febd69] to-[#f0c14b] rounded-lg flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-[#131921]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4" />
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold tracking-tight">ETL Hub</h1>
            <p class="text-xs text-gray-400">PRIDE-C Data Platform</p>
          </div>
        </router-link>

        <nav class="hidden md:flex items-center space-x-1">
          <router-link
            to="/"
            class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
            :class="$route.path === '/' ? 'bg-[#232F3E] text-[#febd69]' : 'text-gray-300 hover:bg-gray-700 hover:text-white'"
          >
            Dashboard
          </router-link>
          <router-link
            to="/forecast"
            class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
            :class="$route.path === '/forecast' ? 'bg-[#232F3E] text-[#febd69]' : 'text-gray-300 hover:bg-gray-700 hover:text-white'"
          >
            Forecast
          </router-link>
        </nav>

        <div class="flex items-center space-x-3">
          <span class="hidden lg:inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-[#febd69] text-[#131921]">
            ETL Hub v1.0
          </span>
          <a
            href="/api/docs"
            target="_blank"
            class="px-3 py-1.5 text-xs font-medium bg-[#232F3E] border border-gray-600 rounded-md text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          >
            API Docs
          </a>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <router-view />
    </main>

    <!-- Footer -->
    <footer class="bg-[#131921] text-gray-400 text-center py-6 mt-auto">
      <p class="text-sm">© 2026 PRIDE-C ETL Hub. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

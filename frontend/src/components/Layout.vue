<!-- Layout.vue -->
<template>
  <div class="min-h-screen bg-gray-900 text-gray-100">
    <!-- Top Header -->
    <header class="bg-gray-800 border-b border-gray-700">
      <div class="flex items-center justify-between px-4 py-2">
        <!-- Logo and Menu Button -->
        <div class="flex items-center space-x-4">
          <button 
            @click="toggleSidebar"
            class="p-2 hover:bg-gray-700 rounded-md transition-colors"
          >
            <Menu class="w-5 h-5" />
          </button>
          <div class="flex items-center space-x-2">
            <Database class="w-8 h-8 text-orange-400" />
            <span class="text-xl font-bold">ETL Dashboard</span>
          </div>
        </div>

        <!-- Search Bar -->
        <div class="flex-1 max-w-2xl mx-8">
          <div class="relative">
            <input
              type="text"
              placeholder="Search data, reports, services..."
              class="w-full px-4 py-2 pl-10 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            />
            <Search class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          </div>
        </div>

        <!-- User Actions -->
        <div class="flex items-center space-x-4">
          <button class="p-2 hover:bg-gray-700 rounded-md transition-colors relative">
            <Bell class="w-5 h-5" />
            <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">3</span>
          </button>
          <div class="flex items-center space-x-2">
            <div class="w-8 h-8 bg-orange-400 rounded-full flex items-center justify-center">
              <User class="w-5 h-5 text-gray-900" />
            </div>
            <span class="text-sm">Admin</span>
            <ChevronDown class="w-4 h-4" />
          </div>
        </div>
      </div>
    </header>

    <div class="flex">
      <!-- Sidebar -->
      <aside 
        :class="[
          'bg-gray-800 border-r border-gray-700 transition-all duration-300 ease-in-out',
          sidebarOpen ? 'w-64' : 'w-16'
        ]"
      >
        <nav class="p-4">
          <ul class="space-y-2">
            <li>
              <router-link
                to="/dashboard"
                :class="[
                  'flex items-center space-x-3 px-3 py-2 rounded-md transition-colors',
                  $route.path === '/dashboard' 
                    ? 'bg-orange-400 text-gray-900' 
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                ]"
              >
                <BarChart3 class="w-5 h-5 flex-shrink-0" />
                <span v-if="sidebarOpen" class="font-medium">Dashboard</span>
              </router-link>
            </li>
            <li>
              <router-link
                to="/data-fetch"
                :class="[
                  'flex items-center space-x-3 px-3 py-2 rounded-md transition-colors',
                  $route.path === '/data-fetch' 
                    ? 'bg-orange-400 text-gray-900' 
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                ]"
              >
                <Download class="w-5 h-5 flex-shrink-0" />
                <span v-if="sidebarOpen" class="font-medium">Data Fetch</span>
              </router-link>
            </li>
            <li>
              <router-link
                to="/forecasting"
                :class="[
                  'flex items-center space-x-3 px-3 py-2 rounded-md transition-colors',
                  $route.path === '/forecasting' 
                    ? 'bg-orange-400 text-gray-900' 
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                ]"
              >
                <TrendingUp class="w-5 h-5 flex-shrink-0" />
                <span v-if="sidebarOpen" class="font-medium">Forecasting</span>
              </router-link>
            </li>
            <li>
              <router-link
                to="/reports"
                :class="[
                  'flex items-center space-x-3 px-3 py-2 rounded-md transition-colors',
                  $route.path === '/reports' 
                    ? 'bg-orange-400 text-gray-900' 
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                ]"
              >
                <FileText class="w-5 h-5 flex-shrink-0" />
                <span v-if="sidebarOpen" class="font-medium">Reports</span>
              </router-link>
            </li>
          </ul>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="flex-1 overflow-auto">
        <!-- Breadcrumb -->
        <div class="bg-gray-850 border-b border-gray-700 px-6 py-3">
          <nav class="flex items-center space-x-2 text-sm">
            <router-link to="/dashboard" class="text-orange-400 hover:text-orange-300">Home</router-link>
            <ChevronRight class="w-4 h-4 text-gray-500" />
            <span class="text-gray-300 capitalize">{{ currentPageName }}</span>
          </nav>
        </div>

        <!-- Page Content -->
        <div class="p-6">
          <slot />
        </div>

        <!-- Footer -->
        <footer class="bg-gray-800 border-t border-gray-700 mt-auto">
          <div class="px-6 py-4">
            <div class="flex items-center justify-between text-sm text-gray-400">
              <div class="flex items-center space-x-4">
                <span>&copy; 2025 ETL Dashboard. All rights reserved.</span>
                <span>|</span>
                <a href="#" class="hover:text-gray-300">Privacy Policy</a>
                <span>|</span>
                <a href="#" class="hover:text-gray-300">Terms of Service</a>
              </div>
              <div class="flex items-center space-x-2">
                <span>Version 1.0.0</span>
                <span>|</span>
                <span class="flex items-center space-x-1">
                  <div class="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>Healthy</span>
                </span>
              </div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Menu,
  Database,
  Search,
  Bell,
  User,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Download,
  TrendingUp,
  FileText,
  Activity
} from 'lucide-vue-next'

// Reactive state
const sidebarOpen = ref(true)
const route = useRoute()

// Methods
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

// Computed properties
const currentPageName = computed(() => {
  const path = route.path.substring(1)
  return path.replace('-', ' ') || 'dashboard'
})
</script>

<style scoped>
/* Custom gray-850 for breadcrumb */
.bg-gray-850 {
  background-color: #1f2937;
}
</style>
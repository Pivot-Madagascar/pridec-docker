<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { ref, computed } from 'vue'
import {
  Menu,
  Database,
  Search,
  Bell,
  ChevronRight,
  BarChart3,
  Download,
  FileText,
  Activity,
  LogOut,
  CloudUpload
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const sidebarOpen = ref(true)

// Navigation items
const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/data-fetch', label: 'Data Fetch', icon: Download },
  { to: '/forecasting', label: 'Forecasting', icon: Activity },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/forecast-post', label: 'Post Forecast', icon: CloudUpload },
]

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}

// Check if current route should show layout
const shouldShowLayout = computed(() => {
  return !route.meta.hideLayout && route.path !== '/login' && route.path !== '/register'
})

// Get current page name for breadcrumb
const currentPageName = computed(() => {
  const path = route.path.substring(1)
  return path.replace('-', ' ') || 'dashboard'
})
</script>

<template>
  <!-- Login/Register pages without layout -->
  <div v-if="!shouldShowLayout">
    <router-view />
  </div>

  <!-- Main app with layout -->
  <div v-else class="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200">
    <!-- Top Header -->
    <header class="bg-amazon-dark text-white px-6 py-4">
      <div class="flex items-center justify-between">
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
            <span class="text-xl font-bold">PRIDE-C ETL</span>
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
          <button
            @click="router.push('/data-fetch')"
            class="amazon-button px-4 py-2 rounded text-sm font-semibold hover:opacity-90"
          >
            Fetch Data
          </button>
          <button
            @click="router.push('/forecast-post')"
            class="amazon-button px-4 py-2 rounded text-sm font-semibold hover:opacity-90"
          >
            New Forecast
          </button>
          <button class="p-2 hover:bg-gray-700 rounded-md transition-colors relative">
            <Bell class="w-5 h-5" />
            <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">3</span>
          </button>
          <button
            @click="logout"
            class="amazon-button px-4 py-2 rounded text-sm font-semibold hover:opacity-90 bg-red-600 text-white border-red-700 flex items-center space-x-2"
          >
            <LogOut class="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>

    <div class="flex">
      <!-- Sidebar -->
      <aside 
        :class="[
          'bg-amazon-dark border-r border-gray-700 transition-all duration-300 ease-in-out',
          sidebarOpen ? 'w-64' : 'w-16'
        ]"
      >
        <nav class="p-4">
          <ul class="space-y-2">
            <li v-for="item in nav" :key="item.to">
              <router-link
                :to="item.to"
                :class="[
                  'flex items-center space-x-3 px-3 py-2 rounded-md transition-colors',
                  $route.path === item.to || ($route.path === '/' && item.to === '/dashboard')
                    ? 'bg-orange-400 text-gray-900' 
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                ]"
              >
                <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
                <span v-if="sidebarOpen" class="font-medium">{{ item.label }}</span>
              </router-link>
            </li>
          </ul>
        </nav>
      </aside>

      <!-- Main Content Area -->
      <div class="flex-1 flex flex-col">
        <!-- Breadcrumb -->
        <div class="amazon-gradient border-b border-gray-300 dark:border-gray-700 px-6 py-3">
          <nav class="flex items-center space-x-2 text-sm">
            <router-link to="/dashboard" class="text-orange-600 dark:text-orange-400 hover:text-orange-500 dark:hover:text-orange-300">Home</router-link>
            <ChevronRight class="w-4 h-4 text-gray-500" />
            <span class="text-gray-700 dark:text-gray-300 capitalize">{{ currentPageName }}</span>
          </nav>
        </div>

        <!-- Main Content -->
        <main class="flex-1 p-6 amazon-gradient overflow-y-auto transition-colors duration-200">
          <div class="max-w-7xl mx-auto">
            <div class="amazon-card bg-white dark:bg-gray-800 rounded p-6 transition-colors duration-200">
              <router-view />
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<style scoped>
.amazon-gradient {
  background: linear-gradient(to bottom, #131921, #232F3E);
}

.amazon-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid #DDD;
}
.dark .amazon-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  border: 1px solid #444;
}
.amazon-button {
  background: linear-gradient(to bottom, #f7dfa5, #f0c14b);
  border: 1px solid #a88734;
  color: #111;
}
.dark .amazon-button {
  background: linear-gradient(to bottom, #565656, #444);
  border: 1px solid #333;
  color: #fff;
}

/* Amazon dark theme */
.bg-amazon-dark {
  background-color: #131921;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #374151;
}

::-webkit-scrollbar-thumb {
  background: #6b7280;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>
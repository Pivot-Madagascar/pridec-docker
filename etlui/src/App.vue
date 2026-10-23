<template>
  <!-- A manual popover puts the toasts in the top layer, above native <dialog> modals (BaseDialog re-raises it). -->
  <div ref="toasts" popover="manual" data-toasts class="toast-layer">
    <Toaster position="bottom-right" />
  </div>
  <div class="app-container">
    <!-- Top Navbar -->
    <header class="app-header">
      <div class="app-header-content">
<router-link to="/" class="app-logo">
          <div class="logo-icon">
            <Icon :path="ICONS.database" class="icon-md" />
          </div>
          <div>
            <h1 class="logo-title">ETL Hub</h1>
            <p class="logo-subtitle">PRIDE-C Data Platform</p>
          </div>
        </router-link>

        <div class="header-right">
          <button
            class="hamburger-btn"
            @click="isDrawerOpen = true"
          >
            <Icon :path="ICONS.menu" class="icon-md" />
          </button>

          <Drawer
            v-model="isDrawerOpen"
            side="right"
            :items="navItems"
            :api-base-url="apiBaseUrl"
          />

          <span class="app-badge">ETL Hub v1.0</span>
          <a
            :href="`${apiBaseUrl}/docs`"
            target="_blank"
            class="nav-link-secondary"
          >
            API Docs
          </a>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
/* The popover box covers the viewport without catching clicks; the Toaster places itself inside. */
.toast-layer {
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  overflow: visible;
  pointer-events: none;
}

@reference "tailwindcss";

.app-container {
  @apply min-h-screen;
}

.app-header {
  @apply px-6 py-4 shadow-lg;
  background-color: #131921;
  color: white;
}

.app-header-content {
  @apply max-w-7xl mx-auto flex items-center justify-between;
}

.app-logo {
  @apply flex items-center space-x-3 transition-opacity;
  text-decoration: none;
  color: inherit;
}

.app-logo:hover {
  @apply opacity-80;
}

.logo-icon {
  @apply w-10 h-10 rounded-lg flex items-center justify-center;
  background: linear-gradient(to bottom right, #febd69, #f0c14b);
}

.logo-icon .icon-md {
  @apply h-6 w-6;
  color: #131921;
}

.logo-title {
  @apply text-xl font-bold tracking-tight;
}

.logo-subtitle {
  @apply text-xs;
  color: #9ca3af;
}

.hamburger-btn {
  @apply p-2 rounded-md transition-colors;
  color: #d1d5db;
}

.hamburger-btn:hover {
  @apply bg-gray-700 text-white;
}

.header-right {
  @apply flex items-center space-x-3;
}

.app-badge {
  @apply hidden lg:inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold;
  background-color: #febd69;
  color: #131921;
}

.nav-link-secondary {
  @apply hidden lg:inline-flex px-3 py-1.5 text-xs font-medium rounded-md transition-colors;
  text-decoration: none;
  background-color: #232F3E;
  border: 1px solid #4b5563;
  color: #d1d5db;
}

.nav-link-secondary:hover {
  @apply bg-gray-700 text-white;
}

.main-content {
  @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Icon, { ICONS } from '@/components/Icons'
import Drawer from '@/components/Drawer.vue'
import { Toaster } from 'vue3-hot-toast'

const toasts = ref<HTMLElement>()
onMounted(() => toasts.value?.showPopover?.()) // without the Popover API the div simply stays in the page

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111'
const isDrawerOpen = ref(false)

const navItems = computed(() => [
  { to: '/', label: 'Dashboard' },
  { to: '/tracking', label: 'Tracking' },
  { to: '/journal', label: 'Journal' },
  { to: '/logs', label: 'Logs' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/parameters', label: 'Parameters' },
  { to: '/admin/config', label: 'Admin Config' }
])
</script>
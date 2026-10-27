<template>
  <!-- A manual popover puts the toasts in the top layer, above the dialogs (portals with a z-index). -->
  <div ref="toasts" popover="manual" data-toasts class="toast-layer">
    <Toaster position="bottom-right" />
  </div>
  <div class="app-container">
    <!-- Top Navbar -->
    <header class="app-header">
      <div class="app-header-content">
<router-link to="/" class="app-logo">
          <div class="logo-icon">
            <Database class="icon-md" />
          </div>
          <div>
            <h1 class="logo-title">ETL Hub</h1>
            <p class="logo-subtitle">PRIDE-C Data Platform</p>
          </div>
        </router-link>

        <div class="header-right">
          <ThemeToggle />
          <Button variant="ghost" size="icon" aria-label="Open the menu" @click="isDrawerOpen = true">
            <Menu class="size-6" />
          </Button>

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

@reference "./styles/base.css";

.app-container {
  @apply min-h-screen;
}

.app-header {
  @apply px-6 py-4 border-b bg-card text-card-foreground;
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
  @apply w-10 h-10 rounded-lg flex items-center justify-center bg-primary text-primary-foreground;
}

.logo-title {
  @apply text-xl font-bold tracking-tight;
}

.logo-subtitle {
  @apply text-xs text-muted-foreground;
}

.header-right {
  @apply flex items-center space-x-3;
}

.app-badge {
  @apply hidden lg:inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-primary/15 text-primary;
}

.nav-link-secondary {
  @apply hidden lg:inline-flex px-3 py-1.5 text-xs font-medium rounded-md transition-colors border bg-secondary text-secondary-foreground hover:bg-secondary/80;
  text-decoration: none;
}

.main-content {
  @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Database, Menu } from '@lucide/vue'
import Drawer from '@/components/Drawer.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { Toaster } from 'vue3-hot-toast'
import { Button } from '@/components/ui/button'

const toasts = ref<HTMLElement>()
onMounted(() => toasts.value?.showPopover?.()) // without the Popover API the div simply stays in the page

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111'
const isDrawerOpen = ref(false)

const navItems = computed(() => [
  { to: '/', label: 'Home' },
  { to: '/tracking', label: 'Tracking' },
  { to: '/journal', label: 'Journal' },
  { to: '/logs', label: 'Logs' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/parameters', label: 'Parameters' },
  { to: '/admin/config', label: 'Admin Config' }
])
</script>
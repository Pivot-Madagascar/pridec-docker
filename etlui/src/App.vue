<template>
  <!-- A manual popover puts the toasts in the top layer, above the dialogs (portals with a z-index). -->
  <div ref="toasts" popover="manual" data-toasts class="toast-layer">
    <Toaster position="bottom-right" />
  </div>

  <!-- Login: the page alone, no menu. -->
  <router-view v-if="route.meta.public" />
  <!-- shadcn Sidebar: the side menu (open or folded, kept in its cookie), then the top bar and the page. -->
  <SidebarProvider v-else>
    <AppSidebar />
    <SidebarInset>
      <!-- Stays at the top while the page scrolls, under the dialogs (z-50). -->
      <header class="sticky top-0 z-20 flex min-h-14 shrink-0 flex-wrap items-center gap-x-2 border-b bg-card px-4 py-2 text-card-foreground">
        <SidebarTrigger class="-ml-1" />
        <Separator orientation="vertical" class="mx-1 data-[orientation=vertical]:h-4" />
        <h1 class="truncate text-base font-medium">{{ route.meta.label }}</h1>
        <!-- A page's breadcrumb (<Teleport to="#app-crumbs">, Forecast): beside the title, on its own line on a phone. -->
        <div id="app-crumbs" class="order-last min-w-0 basis-full empty:hidden md:order-none md:ml-1 md:basis-auto md:border-l md:pl-3" />
        <div class="ml-auto flex items-center gap-2">
          <ModeBadge />
          <ThemeToggle />
          <Button variant="ghost" size="icon" as-child>
            <router-link to="/parameters" aria-label="Parameters"><Settings /></router-link>
          </Button>
          <span v-if="userName" class="hidden text-sm font-medium sm:inline" data-test="user-name">{{ userName }}</span>
        </div>
      </header>
      <!-- From md (the menu beside the page): 95% of the space left of the menu, centred; a 1rem gutter on a phone. -->
      <div class="mx-auto w-full px-4 pt-4 pb-8 md:w-[95%] md:px-0">
        <router-view />
      </div>
    </SidebarInset>
  </SidebarProvider>
  <LoadingScreen v-if="routeLoading">Loading…</LoadingScreen>
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
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Settings } from '@lucide/vue'
import { Toaster } from 'vue3-hot-toast'
import AppSidebar from '@/components/AppSidebar.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import ModeBadge from '@/components/ModeBadge.vue'
import LoadingScreen from '@/components/LoadingScreen.vue'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { routeLoading } from '@/router/loading'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const userName = computed(() => auth.user?.displayName || auth.user?.username)

const toasts = ref<HTMLElement>()
onMounted(() => toasts.value?.showPopover?.()) // without the Popover API the div simply stays in the page
</script>

<template>
  <!-- The app's side menu (shadcn Sidebar, laid out like its block sidebar-07): folds to icons, a Sheet on a phone. -->
  <Sidebar collapsible="icon">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton as-child size="lg" tooltip="ETL Hub">
            <router-link to="/" @click="setOpenMobile(false)">
              <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Database class="size-4" />
              </span>
              <span class="grid leading-tight">
                <span class="font-semibold">ETL Hub</span>
                <span class="text-xs text-muted-foreground">PRIDE-C Data Platform</span>
              </span>
            </router-link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup>
        <SidebarMenu>
          <SidebarMenuItem v-for="item in NAV" :key="item.to">
            <!-- The active entry is filled with the primary colour (the reference's menu). -->
            <SidebarMenuButton
              as-child
              :is-active="isActive(item.to)"
              :tooltip="item.label"
              class="data-[active=true]:bg-primary data-[active=true]:text-primary-foreground data-[active=true]:hover:bg-primary/90 data-[active=true]:hover:text-primary-foreground"
            >
              <router-link :to="item.to" data-test="nav-item" @click="setOpenMobile(false)">
                <component :is="item.icon" />
                <span>{{ item.label }}</span>
              </router-link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton as-child tooltip="API Docs">
            <a :href="`${apiBaseUrl}/docs`" target="_blank">
              <FileCode />
              <span>API Docs</span>
            </a>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton tooltip="Log out" class="text-destructive hover:text-destructive" data-test="logout" @click="auth.logout()">
            <LogOut />
            <span>Log out</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
      <p class="px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">ETL Hub v1.0</p>
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Activity, BookOpen, ChartLine, Database, FileCode, LogOut, Play, ScrollText, Settings } from '@lucide/vue'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarRail, useSidebar
} from '@/components/ui/sidebar'
import { useAuthStore } from '@/stores/auth'

const NAV = [
  { to: '/', label: 'Start a pass', icon: Play },
  { to: '/forecast', label: 'Forecast', icon: ChartLine },
  { to: '/journal', label: 'Journal', icon: BookOpen },
  { to: '/tracking', label: 'Tracking', icon: Activity },
  { to: '/logs', label: 'Logs', icon: ScrollText },
  { to: '/parameters', label: 'Parameters', icon: Settings }
]

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111'
const auth = useAuthStore()
const route = useRoute()
const { setOpenMobile } = useSidebar() // a click on a phone closes the menu's Sheet

const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
</script>

<template>
  <div>
    <transition name="fade">
      <div
        v-if="modelValue"
        class="drawer-overlay"
        @click="close"
      />
    </transition>

    <transition name="slide">
      <aside
        v-if="modelValue"
        class="drawer"
        :data-side="side"
      >
        <div class="drawer-header">
          <button
            class="drawer-close"
            @click="close"
          >
            <Icon :path="ICONS.close" class="h-5 w-5" />
          </button>
        </div>
        <nav class="drawer-nav">
          <router-link
            v-for="item in items"
            :key="item.to"
            :to="item.to"
            class="drawer-link"
            @click="close"
          >
            {{ item.label }}
          </router-link>
          <a
            v-if="apiBaseUrl"
            :href="`${apiBaseUrl}/docs`"
            target="_blank"
            class="drawer-link"
            @click="close"
          >
            API Docs
          </a>
        </nav>
      </aside>
    </transition>
  </div>
</template>

<script setup lang="ts">
import Icon, { ICONS } from '@/components/Icons'

interface NavItem {
  to: string
  label: string
}

interface Props {
  modelValue: boolean
  side?: 'left' | 'right'
  items?: NavItem[]
  apiBaseUrl?: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

withDefaults(defineProps<Props>(), {
  side: 'right',
  items: () => []
})

const emit = defineEmits<Emits>()

function close() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
@reference "tailwindcss";

.drawer-overlay {
  @apply fixed inset-0 bg-black opacity-50 z-40;
}

.drawer {
  @apply fixed top-0 h-full w-64 bg-[#131921] text-white z-50 flex flex-col;
  background-color: #131921;
}

.drawer[data-side="right"] {
  @apply right-0;
}

.drawer[data-side="left"] {
  @apply left-0;
}

.drawer-header {
  @apply flex justify-end p-4;
}

.drawer-close {
  @apply p-2 rounded-md transition-colors;
  color: #d1d5db;
}

.drawer-close:hover {
  @apply bg-gray-700 text-white;
}

.drawer-nav {
  @apply flex flex-col px-4 py-2 space-y-1;
}

.drawer-link {
  @apply px-4 py-3 rounded-md text-sm font-medium transition-colors;
  text-decoration: none;
  color: #d1d5db;
}

.drawer-link:hover {
  @apply bg-gray-700 text-white;
}

.drawer-link.router-link-active {
  @apply bg-[#232F3E] text-[#febd69];
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from[data-side="right"],
.slide-leave-to[data-side="right"] {
  transform: translateX(100%);
}

.slide-enter-from[data-side="left"],
.slide-leave-to[data-side="left"] {
  transform: translateX(-100%);
}
</style>
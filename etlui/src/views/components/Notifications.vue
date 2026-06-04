<template>
  <transition name="fade">
    <div v-if="notification" class="notification" :class="notificationType === 'success' ? 'notification-success' : 'notification-error'">
      <div class="flex-row-center">
        <svg v-if="notificationType === 'success'" xmlns="http://www.w3.org/2000/svg" class="notification-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="notification-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="notification-message">{{ notification }}</span>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
const props = defineProps<{
  notification: string
  notificationType: 'success' | 'error'
}>()
</script>
<script setup lang="ts">
import { watch } from 'vue'
import toast from 'vue3-hot-toast'

const props = defineProps<{
  notification: string
  notificationType: 'success' | 'error'
}>()

watch(
  () => props.notification,
  (msg) => {
    if (msg) {
      if (props.notificationType === 'success') {
        toast.success(msg, { duration: 5000 })
      } else {
        toast.error(msg, { duration: 5000 })
      }
    }
  },
  [props.notification, props.notificationType]
)
</script>

<template>
  <div></div>
</template>
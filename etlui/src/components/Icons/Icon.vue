<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="className"
    v-bind="$attrs"
  >
    <path :d="path" />
  </svg>
</template>

<script setup lang="ts">
defineProps<{
  path: string
  className?: string
}>()
</script>

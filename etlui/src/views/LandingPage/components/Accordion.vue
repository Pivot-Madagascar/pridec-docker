<template>
  <div class="accordion">
    <div
      v-for="(item, index) in items"
      :key="item.id"
      class="accordion-item"
    >
      <button
        class="accordion-header"
        @click="toggle(index)"
      >
        <span class="accordion-title">{{ item.title }}</span>
        <span class="accordion-icon">
          <svg
            :class="{ 'rotate-180': openIndices.includes(index) }"
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m6 9 6 6 6-6"/>
          </svg>
        </span>
      </button>
      <div
        class="accordion-content-wrapper"
        :class="{ 'open': openIndices.includes(index) }"
      >
        <div class="accordion-content">
          <slot :name="`content-${item.id}`" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface AccordionItem {
  id: string
  title: string
}

const props = defineProps<{
  items: AccordionItem[]
  defaultOpen?: string[]
}>()

const emit = defineEmits<{
  'open-change': [index: number, isOpen: boolean]
}>()

const openIndices = ref<number[]>([])

watch(
  () => props.defaultOpen,
  (ids) => {
    if (ids) {
      openIndices.value = ids
        .map(id => props.items.findIndex(item => item.id === id))
        .filter(i => i !== -1)
    }
  },
  { immediate: true }
)

const toggle = (index: number) => {
  const idx = openIndices.value.indexOf(index)
  if (idx !== -1) {
    openIndices.value.splice(idx, 1)
    emit('open-change', index, false)
  } else {
    openIndices.value.push(index)
    emit('open-change', index, true)
  }
}
</script>

<style scoped>
@reference "tailwindcss";

.accordion {
  background: #0f172a;
  border-radius: 1rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.accordion-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.accordion-item:last-child {
  border-bottom: none;
}

.accordion-header {
  width: 100%;
  background: #1e293b;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  border: none;
  outline: none;
  transition: all 0.3s ease;
}

.accordion-header:hover {
  background: #334155;
}

.accordion-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f1f5f9;
}

.accordion-icon {
  color: #94a3b8;
  transition: transform 0.3s ease;
}

.accordion-icon svg {
  width: 20px;
  height: 20px;
}

.rotate-180 {
  transform: rotate(180deg);
}

.accordion-content-wrapper {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
  
}

.accordion-content-wrapper.open {
  max-height: 2000px;
}

.accordion-content {
  padding: 1rem 1.5rem 0 1.5rem;
}
</style>

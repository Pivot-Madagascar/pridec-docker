<template>
  <div class="stepper-carousel">
    <div class="stepper-track">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="stepper-item"
        :class="{ active: currentStep === index, completed: currentStep > index }"
        @click="goToStep(index)"
      >
        <div class="stepper-dot" :class="getStepStatusClass(index)">
          <Icon v-if="isStepCompleted(index)" :path="ICONS.check" :stroke-width="3" class="step-check" />
          <span v-else class="step-number">{{ index + 1 }}</span>
        </div>
        <span class="step-label">{{ step.title }}</span>
      </div>
    </div>

    <div class="carousel-viewport">
      <transition name="fade-slide" mode="out-in">
        <div :key="currentStep" class="step-card">
          <div class="step-card-header">
            <h3 class="step-card-title">{{ steps[currentStep].title }}</h3>
            <div class="flex items-center gap-2">
              <button 
                v-if="steps[currentStep].onRefresh" 
                class="header-refresh-btn" 
                @click="steps[currentStep].onRefresh"
                title="Refresh"
              >
                <Icon :path="ICONS.refresh" />
              </button>
              <button 
                v-if="steps[currentStep].onReset" 
                class="header-reset-btn" 
                @click="steps[currentStep].onReset"
                title="Reset"
              >
                <Icon :path="ICONS.reset" />
              </button>
              <span class="step-card-badge">Step {{ currentStep + 1 }}</span>
            </div>
          </div>
          <div class="action-grid" v-if="steps[currentStep].type !== 'custom' && steps[currentStep].actions?.length" :class="{ gapless: (steps[currentStep].actions?.length || 0) <= 2 }">
            <button
              v-for="action in steps[currentStep].actions"
              :key="action.key"
              :disabled="action.inactive || action.loading"
              class="action-card"
              :class="[
                action.class,
                { 'card-success': action.success }
              ]"
              @click="action.onClick ? action.onClick() : $emit('action-click', action.key)"
            >
              <div class="card-icon" :class="action.iconClass">
                <Icon v-if="action.icon" :path="action.icon" class="icon-svg" />
              </div>
              <div class="card-content">
                <span class="card-title">{{ action.label }}</span>
                <span v-if="action.subtitle" class="card-subtitle">{{ action.subtitle }}</span>
                <span v-if="action.statusText" class="card-status" :class="action.statusClass">
                  <span v-if="action.loading" class="status-running">
                    <span class="spinner"></span>
                    {{ action.loadingText }}
                  </span>
                  <span v-else-if="action.success" class="status-done">{{ action.successText }}</span>
                  <span v-else class="status-pending">{{ action.statusText }}</span>
                </span>
              </div>
            </button>
          </div>
          <slot :name="steps[currentStep].id" :step="steps[currentStep]" />
        </div>
      </transition>
    </div>

    <div class="carousel-controls">
      <button class="control-btn control-prev" :disabled="currentStep === 0" @click="prevStep">
        <Icon :path="ICONS.prev" />
        <span>Previous</span>
      </button>
      <button class="control-btn control-next" :disabled="!canProceedNext" @click="nextStep">
        <span>Next</span>
        <Icon :path="ICONS.next" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Icon from '@/components/Icons'
import { ICONS } from '@/components/Icons'

interface Action {
  key: string
  label: string
  subtitle?: string
  icon?: string
  iconClass: string
  class?: string
  inactive?: boolean
  loading?: boolean
  success?: boolean
  statusText?: string
  statusClass?: string
  loadingText?: string
  successText?: string
  onClick?: () => void
}

interface Step {
  id: string
  title: string
  actions?: Action[]
  type?: 'actions' | 'custom'
  canProceed?: boolean
  onRefresh?: () => void
  onReset?: () => void
}

const props = defineProps<{
  steps: Step[]
  initialStep?: number
}>()

const emit = defineEmits<{
  'action-click': [key: string]
  'step-change': [index: number]
}>()

const currentStep = ref(props.initialStep || 0)

const isStepCompleted = (index: number) => {
  return currentStep.value > index
}

const getStepStatusClass = (index: number) => {
  if (isStepCompleted(index)) return 'step-done'
  if (currentStep.value === index) return 'step-active'
  return 'step-pending'
}

const goToStep = (index: number) => {
  currentStep.value = index
  emit('step-change', index)
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value -= 1
    emit('step-change', currentStep.value)
  }
}

const nextStep = () => {
  if (currentStep.value < props.steps.length - 1) {
    currentStep.value += 1
    emit('step-change', currentStep.value)
  }
}

const canProceedNext = computed(() => {
  const currentStepData = props.steps[currentStep.value]
  return currentStep.value < props.steps.length - 1 && currentStepData.canProceed !== false
})
</script>

<style scoped>
/* ===== Stepper Carousel Layout ===== */
.stepper-carousel {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.stepper-track {
  display: flex;
  justify-content: space-between;
  position: relative;
  padding: 0 1rem;
}

.stepper-track::before {
  content: '';
  position: absolute;
  top: 1.35rem;
  left: 1.5rem;
  right: 1.5rem;
  height: 2px;
  background: #334155;
  z-index: 0;
}

.stepper-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  z-index: 1;
  position: relative;
}

.stepper-dot {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e293b;
  color: #94a3b8;
  border: 2px solid #334155;
  transition: all 0.3s ease;
  position: relative;
}

.stepper-item:hover .step-pending {
  border-color: #6366f1;
  color: #a5b4fc;
}

.step-check {
  width: 1rem;
  height: 1rem;
  color: #10b981;
}

.step-number {
  font-weight: 600;
  font-size: 0.875rem;
}

.step-active {
  background: #6366f1;
  border-color: #6366f1;
  color: white;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
}

.step-done {
  background: #10b981;
  border-color: #10b981;
  color: white;
}

.step-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: #64748b;
  text-align: center;
}

.step-active + .step-label {
  color: #e2e8f0;
  font-weight: 600;
}

.step-done + .step-label {
  color: #10b981;
}

/* ===== Carousel Viewport ===== */
.carousel-viewport {
  min-height: 280px;
  position: relative;
  overflow: hidden;
}

.step-card {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.step-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.step-card-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f1f5f9;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.step-card-badge {
  font-size: 0.75rem;
  font-weight: 500;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.15);
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.header-refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.375rem;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.header-refresh-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
}

.header-refresh-btn svg,
.header-reset-btn svg {
  width: 14px;
  height: 14px;
}

.header-reset-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 0.375rem;
  color: #f87171;
  cursor: pointer;
  transition: all 0.2s ease;
}

.header-reset-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

/* ===== Action Grid ===== */
.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.action-grid.gapless {
  grid-template-columns: repeat(2, 1fr);
  max-width: calc(66.666% + 1rem);
}

.action-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.75rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  text-align: left;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.action-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top left, rgba(99, 102, 241, 0.1), transparent 60%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-card:hover:not(:disabled)::before {
  opacity: 1;
}

.action-card:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(99, 102, 241, 0.1);
  transform: translateY(-4px);
}

.action-card:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.action-card.card-success {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}

.card-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

.icon-svg {
  width: 1.25rem;
  height: 1.25rem;
  color: white;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.card-title {
  font-weight: 600;
  font-size: 0.9375rem;
  color: #f1f5f9;
  display: block;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.card-subtitle {
  font-size: 0.8125rem;
  color: #94a3b8;
  display: block;
}

.card-status {
  font-size: 0.75rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  margin-top: 0.25rem;
}

.status-running {
  color: #fbbf24;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.status-done {
  color: #34d399;
  font-weight: 600;
}

.status-pending {
  color: #64748b;
}

.spinner {
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid #fbbf24;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-40px);
}

/* ===== Carousel Controls ===== */
.carousel-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.control-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  color: #e2e8f0;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:hover:not(:disabled) {
  background: #334155;
  border-color: #6366f1;
}

.control-btn svg {
  width: 20px;
  height: 20px;
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* ===== Icon Colors ===== */
.icon-blue { background: #6366f1; }
.icon-sky { background: #0ea5e9; }
.icon-green { background: #16a34a; }
.icon-teal { background: #0d9488; }
.icon-purple { background: #8b5cf6; }
.icon-indigo { background: #6366f1; }
.icon-orange { background: #ea580c; }
.icon-amber { background: #d97706; }
.icon-rose { background: #e11d48; }
.icon-emerald { background: #059669; }
.icon-slate { background: #64748b; }
.icon-forecast { background: #6366f1; }

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .action-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .action-grid.gapless {
    max-width: 100%;
  }
}

@media (max-width: 640px) {
  .action-grid {
    grid-template-columns: 1fr;
  }
  .action-grid.gapless {
    grid-template-columns: 1fr;
  }
  .step-label {
    font-size: 0.7rem;
  }
}
</style>
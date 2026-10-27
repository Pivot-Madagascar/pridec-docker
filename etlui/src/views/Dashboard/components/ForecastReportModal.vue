<template>
  <Dialog :open="modelValue" @update:open="!$event && closeModal()">
    <!-- Full screen. Opened from the run's "Steps" dialog, it opens last, so it sits above it. -->
    <DialogContent
      class="flex h-screen w-screen max-w-none flex-col gap-0 rounded-none border-0 p-0 sm:max-w-none"
      :aria-describedby="undefined"
    >
      <div class="flex items-center justify-between gap-4 border-b bg-card py-4 pr-14 pl-4">
        <DialogTitle class="text-2xl font-bold">Forecast Report</DialogTitle>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" @click="fetchReport" :disabled="loading">
            <RefreshCw :class="{ 'animate-spin': loading }" />
            <span>Refresh</span>
          </Button>
          <!-- Native download: the browser sends the session cookie and saves the zip itself. New tab so an
               error page (404, expired session) does not replace the app. Open run only: a closed run's files left input/. -->
          <Button v-if="!run" as="a" variant="outline" size="sm" :href="archiveUrl" target="_blank" rel="noopener" download>
            <Icon :path="ICONS.download" stroke-width="2" />
            <span>Download Forecast Data</span>
          </Button>
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-hidden">
        <iframe
          v-if="reportContent"
          :srcdoc="reportContent"
          class="size-full border-none bg-white"
          title="Forecast Report"
        ></iframe>
        <div v-else-if="loading" class="flex h-full flex-col items-center justify-center gap-4">
          <LoaderCircle class="size-12 animate-spin" aria-hidden="true" />
          <p>Loading report...</p>
        </div>
        <div v-else class="flex h-full items-center justify-center text-red-400">
          <p>{{ errorMessage }}</p>
        </div>
      </div>
      <!-- Approve / Reject when the report is opened to decide on it -->
      <div v-if="$slots.footer" class="flex justify-end gap-3 border-t bg-card p-4"><slot name="footer" /></div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '@/services/api'
import { LoaderCircle, RefreshCw } from '@lucide/vue'
import Icon, { ICONS } from '@/components/Icons'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

const props = defineProps<{
  modelValue: boolean
  // A closed run: its archived report. Otherwise the report of the open run, in output/.
  run?: { source: string; disease: string } | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const archiveUrl = api.getUri({ url: '/output/archive' })
const reportContent = ref('')
const loading = ref(false)
const errorMessage = ref('')

const closeModal = () => {
  emit('update:modelValue', false)
}

const fetchReport = async () => {
  loading.value = true
  reportContent.value = ''
  errorMessage.value = ''
  
  try {
    const url = props.run ? `/pipeline/runs/${props.run.source}/${props.run.disease}/report` : '/output/forecast_report.html'
    const response = await api.get(url, { responseType: 'text' })
    reportContent.value = response.data
  } catch (err: any) {
    if (err.response?.status === 404) {
      errorMessage.value = 'Forecast report not found. Run the forecast step first.'
    } else {
      errorMessage.value = 'Failed to load report. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

// Read again at each opening: the report changes with the run.
watch(() => props.modelValue, open => open && fetchReport(), { immediate: true })
</script>

<template>
  <div class="file-input" data-test="file-input">
    <!-- File already in input/ on the server. -->
    <div v-if="serverFile" class="status-row" data-test="status-row" :class="{ 'is-present': serverFile.exists }">
      <template v-if="serverFile.exists">
        <span class="status-dot" aria-hidden="true"></span>
        <span class="status-text">
          On server · {{ formatSize(serverFile.size ?? 0) }}<template v-if="serverFile.modified"> · {{ formatDate(serverFile.modified) }}</template>
        </span>
        <Button variant="outline" size="sm" :aria-label="`Preview ${label} on the server`" @click="emit('preview-server')">
          <Icon :path="ICONS.eye" />
          Preview
        </Button>
        <Button variant="destructive" size="sm" :disabled="busy" :aria-label="`Delete ${label} from the server`" @click="emit('delete')">
          <Icon :path="ICONS.reset" />
          {{ busy ? 'Deleting…' : 'Delete' }}
        </Button>
      </template>
      <span v-else class="status-text">Not on server</span>
    </div>

    <!-- Local file: drop or browse, then preview / replace / remove / upload. -->
    <div
      class="dropzone"
      data-test="dropzone"
      :class="{ 'is-dragging': dragging, 'has-file': modelValue, 'has-error': error, 'is-disabled': disabled }"
      :aria-disabled="disabled"
      @dragover.prevent="dragging = !disabled"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <div class="dropzone-icon">
        <Icon :path="modelValue ? ICONS.checkCircle : ICONS.upload" class="dropzone-icon-svg" />
      </div>

      <div class="dropzone-body">
        <span class="dropzone-title">{{ label }}</span>
        <template v-if="modelValue">
          <span class="dropzone-file">{{ modelValue.name }}</span>
          <span class="dropzone-hint">{{ formatSize(modelValue.size) }}</span>
        </template>
        <template v-else>
          <span class="dropzone-hint">{{ description }}</span>
          <span class="dropzone-hint">
            Drag the file here or
            <label :for="inputId" class="dropzone-link">browse</label>
          </span>
        </template>
        <span v-if="error" class="dropzone-error" role="alert">{{ error }}</span>
      </div>

      <div v-if="modelValue" class="dropzone-actions">
        <Button variant="outline" size="sm" :aria-label="`Preview the selected ${label}`" @click="emit('preview-local', modelValue)">
          <Icon :path="ICONS.eye" />
          Preview
        </Button>
        <Button as="label" :for="inputId" variant="outline" size="sm" :class="{ 'pointer-events-none opacity-50': busy }">Replace</Button>
        <Button variant="destructive" size="sm" :disabled="busy" @click="clear">Remove</Button>
        <Button
          size="sm"
          :disabled="busy || disabled"
          :aria-busy="busy"
          :aria-label="`Upload ${label} to the server`"
          @click="emit('upload', modelValue)"
        >
          <LoaderCircle v-if="busy" class="animate-spin" aria-hidden="true" />
          <Icon v-else :path="ICONS.upload" />
          {{ busy ? 'Uploading…' : 'Upload' }}
        </Button>
      </div>

      <input :id="inputId" ref="input" type="file" :accept="accept" class="sr-only" :disabled="disabled" @change="onChange" />
    </div>

    <!-- The file of the repo (assets/) offered for this item, until a file is on the server: delete that one to get it back. -->
    <div v-if="defaultFile && !serverFile?.exists" class="status-row is-present default-status" data-test="default-status">
      <span class="status-text">Default · {{ defaultFile.filename }} · {{ formatSize(defaultFile.size) }}</span>
      <Button variant="outline" size="sm" :aria-label="`Preview the default ${label}`" @click="emit('preview-default')">
        <Icon :path="ICONS.eye" />
        Preview
      </Button>
      <Button variant="outline" size="sm" :disabled="disabled || busy" :aria-label="`Use the default ${label}`" @click="emit('use-default')">
        Use default
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { LoaderCircle } from '@lucide/vue'
import Icon, { ICONS } from '@/components/Icons'
import { Button } from '@/components/ui/button'
import type { DefaultFile, ServerFile } from '@/types/inputs'

const props = defineProps<{
  modelValue?: File
  label: string
  description: string
  accept: string
  serverFile?: ServerFile
  defaultFile?: DefaultFile
  busy?: boolean
  // Nothing can be selected, dropped or uploaded (the server would refuse it now).
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [file: File | undefined]
  delete: []
  upload: [file: File]
  'preview-local': [file: File]
  'preview-server': []
  'preview-default': []
  'use-default': []
}>()

const inputId = useId()
const input = ref<HTMLInputElement>()
const dragging = ref(false)
const error = ref('')

// --- Selection -------------------------------------------------------------

const extensions = computed(() => props.accept.split(',').filter(ext => ext.startsWith('.')))

const select = (file?: File) => {
  if (!file) return
  if (!extensions.value.some(ext => file.name.toLowerCase().endsWith(ext))) {
    error.value = `Expected a ${extensions.value.join(' or ')} file`
    return
  }
  error.value = ''
  emit('update:modelValue', file)
}

const onChange = (event: Event) => {
  select((event.target as HTMLInputElement).files?.[0])
  if (input.value) input.value.value = '' // lets the same file be picked again
}

const onDrop = (event: DragEvent) => {
  dragging.value = false
  if (!props.disabled) select(event.dataTransfer?.files[0])
}

const clear = () => {
  error.value = ''
  emit('update:modelValue', undefined)
}

// --- Display ---------------------------------------------------------------

const formatSize = (bytes: number) =>
  bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
</script>

<style scoped>
/* --- Dropzone ------------------------------------------------------------ */

.dropzone {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background: #1e293b;
  border: 2px dashed rgba(255, 255, 255, 0.12);
  border-radius: 0.75rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.dropzone:hover,
.dropzone:focus-within,
.dropzone.is-dragging {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
}

.dropzone.has-file {
  border-style: solid;
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.06);
}

.dropzone.has-error {
  border-color: rgba(239, 68, 68, 0.6);
}

.dropzone.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropzone-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.has-file .dropzone-icon {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.dropzone-icon-svg {
  width: 1.5rem;
  height: 1.5rem;
}

.dropzone-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.dropzone-title {
  color: #f1f5f9;
  font-weight: 600;
  font-family: ui-monospace, monospace;
}

.dropzone-file {
  color: #4ade80;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropzone-hint {
  color: #94a3b8;
  font-size: 0.8125rem;
}

.dropzone-link {
  color: #60a5fa;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

.dropzone-error {
  color: #f87171;
  font-size: 0.8125rem;
}

.dropzone-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* --- Status rows (server file, default file) ----------------------------- */

.file-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2rem;
  padding: 0 0.25rem;
  color: #64748b;
  font-size: 0.8125rem;
}

.status-row.is-present {
  color: #94a3b8;
}

.status-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}

.status-text {
  flex: 1;
  min-width: 0;
}

@media (max-width: 640px) {
  .dropzone {
    flex-wrap: wrap;
  }
  .dropzone-actions {
    width: 100%;
  }
}
</style>

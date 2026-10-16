<template>
  <div class="dropzone-card">
    <div
      class="dropzone"
      :class="{ 'is-dragging': dragging, 'has-file': modelValue, 'has-error': error, 'is-disabled': disabled }"
      :aria-disabled="disabled"
      @dragover.prevent="dragging = !disabled"
      @dragleave.prevent="dragging = false"
      @drop.prevent="!disabled && onDrop($event)"
    >
      <div class="dropzone-icon">
        <Icon :path="modelValue ? ICONS.checkCircle : ICONS.upload" class="icon-svg" />
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
        <button
          type="button"
          class="dropzone-btn dropzone-btn-primary"
          :aria-label="`Preview the selected ${label}`"
          @click="emit('preview-local', modelValue)"
        >
          <Icon :path="ICONS.eye" class="btn-icon" />
          Preview
        </button>
        <label :for="inputId" class="dropzone-btn" :class="{ 'is-disabled': uploading }">Replace</label>
        <button type="button" class="dropzone-btn dropzone-btn-danger" :disabled="uploading" @click="clear">Remove</button>
        <button
          type="button"
          class="dropzone-btn dropzone-btn-upload"
          :disabled="uploading || disabled"
          :aria-busy="uploading"
          :aria-label="`Upload ${label} to the server`"
          @click="emit('upload', modelValue)"
        >
          <span v-if="uploading" class="btn-spinner animate-spin" aria-hidden="true"></span>
          <Icon v-else :path="ICONS.upload" class="btn-icon" />
          {{ uploading ? 'Uploading…' : 'Upload' }}
        </button>
      </div>

      <input
        :id="inputId"
        ref="input"
        type="file"
        :accept="accept"
        class="sr-only"
        :disabled="disabled"
        @change="onChange"
      />
    </div>

    <div v-if="serverFile" class="server-status" :class="{ 'is-present': serverFile.exists }">
      <template v-if="serverFile.exists">
        <span class="server-dot" aria-hidden="true"></span>
        <span class="server-text">
          On server · {{ formatSize(serverFile.size ?? 0) }}<template v-if="serverFile.modified"> · {{ formatDate(serverFile.modified) }}</template>
        </span>
        <button
          type="button"
          class="server-preview"
          :aria-label="`Preview ${label} on the server`"
          @click="emit('preview-server')"
        >
          <Icon :path="ICONS.eye" class="server-delete-icon" />
          Preview
        </button>
        <button
          type="button"
          class="server-delete"
          :disabled="deleting"
          :aria-label="`Delete ${label} from the server`"
          @click="emit('delete')"
        >
          <Icon :path="ICONS.reset" class="server-delete-icon" />
          {{ deleting ? 'Deleting…' : 'Delete' }}
        </button>
      </template>
      <span v-else class="server-text">Not on server</span>
    </div>

    <!-- The file of the repo (assets/) offered for this item: previewable anytime, usable when an upload is. -->
    <div v-if="defaultFile" class="server-status is-present default-status">
      <span class="server-text">Default · {{ defaultFile.filename }} · {{ formatSize(defaultFile.size) }}</span>
      <button type="button" class="server-preview" :aria-label="`Preview the default ${label}`" @click="emit('preview-default')">
        <Icon :path="ICONS.eye" class="server-delete-icon" />
        Preview
      </button>
      <button
        type="button"
        class="server-preview"
        :disabled="disabled || uploading"
        :aria-label="`Use the default ${label}`"
        @click="emit('use-default')"
      >
        Use default
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue'
import Icon, { ICONS } from '@/components/Icons'
import type { DefaultFile, ServerFile } from '@/types/inputs'

const props = defineProps<{
  modelValue?: File
  label: string
  description: string
  accept: string
  serverFile?: ServerFile
  defaultFile?: DefaultFile
  deleting?: boolean
  uploading?: boolean
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

const isAccepted = (file: File) =>
  props.accept.split(',').some(ext => ext.startsWith('.') && file.name.toLowerCase().endsWith(ext))

const select = (file?: File) => {
  if (!file) return
  if (!isAccepted(file)) {
    error.value = `Expected a ${props.accept.split(',').filter(e => e.startsWith('.')).join(' or ')} file`
    return
  }
  error.value = ''
  emit('update:modelValue', file)
}

const onChange = (event: Event) => {
  select((event.target as HTMLInputElement).files?.[0])
  if (input.value) input.value.value = ''
}

const onDrop = (event: DragEvent) => {
  dragging.value = false
  select(event.dataTransfer?.files[0])
}

const clear = () => {
  error.value = ''
  emit('update:modelValue', undefined)
}

const formatSize = (bytes: number) =>
  bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
</script>

<style scoped>
@reference "tailwindcss";

.dropzone.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

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

.icon-svg {
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

.dropzone-btn {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
}

.dropzone-btn:hover {
  background: rgba(255, 255, 255, 0.12);
}

.dropzone-btn-danger:hover {
  color: #fca5a5;
  border-color: rgba(239, 68, 68, 0.5);
}

.server-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2rem;
  margin-top: 0.5rem;
  padding: 0 0.25rem;
  color: #64748b;
  font-size: 0.8125rem;
}

.server-status.is-present {
  color: #94a3b8;
}

.server-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}

.server-text {
  flex: 1;
  min-width: 0;
}

.server-preview {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 0.375rem;
  font-weight: 600;
  color: #93c5fd;
  background: transparent;
  border: 1px solid rgba(59, 130, 246, 0.35);
  cursor: pointer;
}

.server-preview:hover {
  background: rgba(59, 130, 246, 0.12);
}

.server-preview:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dropzone-btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  color: #bfdbfe;
  border-color: rgba(59, 130, 246, 0.4);
}

.dropzone-btn-upload {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  color: #fff;
  background: #2563eb;
  border-color: #2563eb;
}

.dropzone-btn-upload:not(:disabled):hover {
  background: #1d4ed8;
}

.dropzone-btn:disabled,
.dropzone-btn.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-spinner {
  width: 0.875rem;
  height: 0.875rem;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
}

.btn-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.server-delete {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 0.375rem;
  font-weight: 600;
  color: #f87171;
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.35);
  cursor: pointer;
}

.server-delete:not(:disabled):hover {
  background: rgba(239, 68, 68, 0.12);
}

.server-delete:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.server-delete-icon {
  width: 0.875rem;
  height: 0.875rem;
}

@media (max-width: 640px) {
  .dropzone {
    flex-wrap: wrap;
  }
  .dropzone-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

<template>
  <div class="file-input" data-test="file-input">
    <!-- File already in input/ on the server. -->
    <div v-if="serverFile" class="status-row" data-test="status-row" :class="{ 'is-present': serverFile.exists }">
      <template v-if="serverFile.exists">
        <span class="status-dot" aria-hidden="true"></span>
        <span class="status-text">
          On server · {{ formatSize(serverFile.size ?? 0) }}<template v-if="serverFile.modified"> · {{ formatDate(serverFile.modified) }}</template>
        </span>
        <!-- Together on one line, beside the text (icons only on a narrow component), or under it. -->
        <div class="status-actions">
          <Button variant="outline" size="sm" title="Preview" :aria-label="`Preview ${label} on the server`" @click="emit('preview-server')">
            <Eye />
            <span class="action-text">Preview</span>
          </Button>
          <Button variant="destructive" size="sm" :disabled="busy" :title="busy ? 'Deleting…' : 'Delete'"
            :aria-label="`Delete ${label} from the server`" @click="emit('delete')">
            <Trash2 />
            <span class="action-text">{{ busy ? 'Deleting…' : 'Delete' }}</span>
          </Button>
        </div>
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
        <component :is="modelValue ? CircleCheck : Upload" class="dropzone-icon-svg" />
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

      <!-- One line always: on a narrow component the buttons keep their icon only, their name in title and aria-label. -->
      <div v-if="modelValue" class="dropzone-actions">
        <Button variant="outline" size="sm" title="Preview" :aria-label="`Preview the selected ${label}`" @click="emit('preview-local', modelValue)">
          <Eye />
          <span class="action-text">Preview</span>
        </Button>
        <Button as="label" :for="inputId" variant="outline" size="sm" title="Replace" :aria-label="`Replace the selected ${label}`"
          :class="{ 'pointer-events-none opacity-50': busy }">
          <Replace />
          <span class="action-text">Replace</span>
        </Button>
        <Button variant="destructive" size="sm" :disabled="busy" title="Remove" :aria-label="`Remove the selected ${label}`" @click="clear">
          <X />
          <span class="action-text">Remove</span>
        </Button>
        <Button
          size="sm"
          :disabled="busy || disabled"
          :aria-busy="busy"
          :title="busy ? 'Uploading…' : 'Upload'"
          :aria-label="`Upload ${label} to the server`"
          @click="emit('upload', modelValue)"
        >
          <LoaderCircle v-if="busy" class="animate-spin" aria-hidden="true" />
          <Upload v-else />
          <span class="action-text">{{ busy ? 'Uploading…' : 'Upload' }}</span>
        </Button>
      </div>

      <input :id="inputId" ref="input" type="file" :accept="accept" class="sr-only" :disabled="disabled" @change="onChange" />
    </div>

    <!-- The file of the repo (assets/) offered for this item, until a file is on the server: delete that one to get it back. -->
    <div v-if="defaultFile && !serverFile?.exists" class="status-row is-present default-status" data-test="default-status">
      <span class="status-text">Default · {{ defaultFile.filename }} · {{ formatSize(defaultFile.size) }}</span>
      <div class="status-actions">
        <Button variant="outline" size="sm" :aria-label="`Preview the default ${label}`" @click="emit('preview-default')">
          <Eye />
          Preview
        </Button>
        <Button variant="outline" size="sm" :disabled="disabled || busy" :aria-label="`Use the default ${label}`" @click="emit('use-default')">
          Use default
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { CircleCheck, Eye, LoaderCircle, Replace, Trash2, Upload, X } from '@lucide/vue'
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
  background: var(--muted);
  border: 2px dashed var(--border);
  border-radius: 0.75rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.dropzone:hover,
.dropzone:focus-within,
.dropzone.is-dragging {
  border-color: var(--primary);
  background: color-mix(in oklab, var(--primary) 8%, transparent);
}

.dropzone.has-file {
  border-style: solid;
  border-color: color-mix(in oklab, var(--success) 50%, transparent);
  background: color-mix(in oklab, var(--success) 6%, transparent);
}

.dropzone.has-error {
  border-color: color-mix(in oklab, var(--destructive) 60%, transparent);
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
  background: color-mix(in oklab, var(--primary) 15%, transparent);
  color: var(--primary);
}

.has-file .dropzone-icon {
  background: color-mix(in oklab, var(--success) 15%, transparent);
  color: var(--success);
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
  color: var(--foreground);
  font-weight: 600;
  font-family: ui-monospace, monospace;
}

.dropzone-file {
  color: var(--success);
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropzone-hint {
  color: var(--muted-foreground);
  font-size: 0.8125rem;
}

.dropzone-link {
  color: var(--primary);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

.dropzone-error {
  color: var(--destructive);
  font-size: 0.8125rem;
}

.dropzone-actions {
  display: flex;
  flex-wrap: nowrap; /* the 4 buttons on one line (their text hides on a narrow component, below) */
  justify-content: flex-end;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* --- Status rows (server file, default file) ----------------------------- */

.file-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  container-type: inline-size; /* the layout follows the component's width (a narrow Steps column), not the screen's */
}

.status-row {
  display: flex;
  flex-wrap: wrap; /* its buttons go under the text rather than out of the component */
  align-items: center;
  gap: 0.5rem;
  min-height: 2rem;
  padding: 0 0.25rem;
  color: var(--muted-foreground);
  font-size: 0.8125rem;
}

.status-row.is-present {
  color: var(--muted-foreground);
}

.status-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--success) 20%, transparent);
}

.status-text {
  flex: 1 1 10rem;
  min-width: 0;
}

/* A row's buttons never split: they wrap together, right-aligned. */
.status-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: 0.5rem;
  margin-left: auto;
}

/* Too narrow for the file and its 4 buttons side by side: the buttons on their own line, wrapping if needed. */
@container (max-width: 38rem) {
  .dropzone {
    flex-wrap: wrap;
  }
  .dropzone-actions {
    width: 100%;
    flex-shrink: 1;
  }
}

/* Too narrow for 4 buttons with their text (~370px): icons only, still on one line (the server row's 2 as well). */
@container (max-width: 26rem) {
  .action-text {
    display: none;
  }
}
</style>

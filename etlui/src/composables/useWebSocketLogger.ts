import { ref, computed, onUnmounted } from 'vue'

export interface LogEntry {
  type: 'etl_log_entry' | 'job_status_update' | 'etl_log_history' | 'etl_log_complete'
  job_id: string
  timestamp?: string
  level?: string
  message?: string
  source?: string
  status?: string
  final_status?: string
  logs?: string
}

export interface UseWebSocketLoggerOptions {
  baseUrl?: string
}

export function useWebSocketLogger(options: UseWebSocketLoggerOptions = {}) {
  const { baseUrl = '' } = options
  const logs = ref<LogEntry[]>([])
  const history = ref<string>('')
  const status = ref<string>('')
  const statusMessage = ref<string>('')
  const connected = ref(false)
  const connectionError = ref('')

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let currentJobId = ''

  function clearTimers() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function connect(jobId: string) {
    disconnect()
    connectionError.value = ''
    currentJobId = jobId

    const wsUrl = `${baseUrl.replace(/^https?/, 'ws')}/api/tracking/etl-logs/${encodeURIComponent(jobId)}`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        connected.value = true
        reconnectAttempts = 0
        connectionError.value = ''
      }

      ws.onmessage = (event) => {
        try {
          const data: LogEntry = JSON.parse(event.data)

          if (data.type === 'etl_log_history') {
            history.value = data.logs || ''
          } else if (data.type === 'job_status_update') {
            status.value = data.status || 'unknown'
            statusMessage.value = data.message || ''
            logs.value.push(data)
          } else if (data.type === 'etl_log_entry') {
            logs.value.push(data)
          } else if (data.type === 'etl_log_complete') {
            logs.value.push(data)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message', e)
        }
      }

      ws.onerror = () => {
        connectionError.value = 'WebSocket connection error'
      }

      ws.onclose = (event) => {
        connected.value = false
        ws = null

        if (!event.wasClean && reconnectAttempts < maxReconnectAttempts && status.value !== 'success' && status.value !== 'error') {
          reconnectAttempts++
          reconnectTimer = setTimeout(() => connect(jobId), 2000 * reconnectAttempts)
        }
      }
    } catch (e: unknown) {
      connectionError.value = (e as Error)?.message || 'Failed to connect'
      connected.value = false
    }
  }

  function disconnect() {
    clearTimers()
    reconnectAttempts = 0
    currentJobId = ''
    if (ws) {
      ws.onclose = null
      ws.onerror = null
      ws.onmessage = null
      ws.onopen = null
      ws.close()
      ws = null
    }
    connected.value = false
  }

  function clearLogs() {
    logs.value = []
    history.value = ''
    status.value = ''
    statusMessage.value = ''
    connectionError.value = ''
  }

  onUnmounted(() => {
    disconnect()
  })

  const isRunning = computed(() => status.value === 'running' || status.value === 'pending')
  const isCompleted = computed(() => status.value === 'success' || status.value === 'error')

  const combinedLogs = computed(() => {
    const parts: string[] = []
    if (history.value) {
      parts.push(history.value)
    }
    for (const entry of logs.value) {
      if (entry.type === 'etl_log_entry' && entry.message) {
        const line = entry.timestamp ? `${entry.timestamp} [${entry.level || 'INFO'}] ${entry.message}` : entry.message
        parts.push(line)
      }
    }
    return parts.join('\n')
  })

  return {
    logs,
    history,
    status,
    statusMessage,
    connected,
    connectionError,
    connect,
    disconnect,
    clearLogs,
    isRunning,
    isCompleted,
    combinedLogs,
  }
}

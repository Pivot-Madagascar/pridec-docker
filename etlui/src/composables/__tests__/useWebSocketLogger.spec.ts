import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useAuthStore } from '@/stores/auth'
import { useWebSocketLogger, WS_NOT_AUTHENTICATED } from '@/composables/useWebSocketLogger'

class FakeWebSocket {
  static last: FakeWebSocket
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: ((e: { code: number; wasClean: boolean }) => void) | null = null
  constructor(public url: string) { FakeWebSocket.last = this }
  close() {}
}

describe('useWebSocketLogger', () => {
  let location: { href: string }

  beforeEach(() => {
    vi.stubGlobal('WebSocket', FakeWebSocket)
    location = { href: '' }
    vi.spyOn(window, 'location', 'get').mockReturnValue(location as Location)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('sends the user back to /login when etlhub closes with 4401', () => {
    const store = useAuthStore()
    store.setUser({ id: 'u1', email: null, username: 'tester', displayName: 'Tester' })

    useWebSocketLogger({ baseUrl: 'http://localhost:8111' }).connect('import_gee_1234abcd')
    FakeWebSocket.last.onclose!({ code: WS_NOT_AUTHENTICATED, wasClean: true })

    expect(store.isAuthenticated).toBe(false)
    expect(location.href).toBe('/login')
  })

  it('keeps the existing behaviour for 4004 (no history yet)', () => {
    useWebSocketLogger({ baseUrl: 'http://localhost:8111' }).connect('import_gee_1234abcd')
    FakeWebSocket.last.onclose!({ code: 4004, wasClean: true })

    expect(location.href).toBe('')
  })

  it('uses wss:// for an https API and ws:// for http', () => {
    useWebSocketLogger({ baseUrl: 'https://etl.example.org' }).connect('import_gee_1234abcd')
    expect(FakeWebSocket.last.url).toBe('wss://etl.example.org/api/tracking/etl-logs/import_gee_1234abcd')

    useWebSocketLogger({ baseUrl: 'http://localhost:8111' }).connect('import_gee_1234abcd')
    expect(FakeWebSocket.last.url).toBe('ws://localhost:8111/api/tracking/etl-logs/import_gee_1234abcd')
  })
})

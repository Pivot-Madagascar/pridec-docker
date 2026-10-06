import { describe, it, expect, vi, beforeEach } from 'vitest'

const getConfigPreview = vi.fn()
const getExternalDataPreview = vi.fn()
vi.mock('@/services/inputs', () => ({
  getConfigPreview: (...args: unknown[]) => getConfigPreview(...args),
  getExternalDataPreview: (...args: unknown[]) => getExternalDataPreview(...args)
}))

import { useInputPreview, PREVIEW_ROWS } from '@/composables/useInputPreview'

const fakeFile = (text: string) => {
  const bytes = new TextEncoder().encode(text)
  return {
    name: 'picked',
    text: async () => text,
    stream: () => new ReadableStream<Uint8Array>({ start(c) { c.enqueue(bytes); c.close() } })
  } as unknown as File
}

describe('useInputPreview', () => {
  beforeEach(() => vi.clearAllMocks())

  it('previews the server config', async () => {
    getConfigPreview.mockResolvedValue({ a: 1 })
    const { open, current, config, loading } = useInputPreview()

    await open('config', 'server')

    expect(current.value).toEqual({ name: 'config', source: 'server' })
    expect(config.value).toEqual({ a: 1 })
    expect(loading.value).toBe(false)
  })

  it('previews the server CSV with 100 rows max', async () => {
    const data = { columns: ['a'], rows: [['1']], total_rows: 1, period_range: null, org_units: 0 }
    getExternalDataPreview.mockResolvedValue(data)
    const { open, csv } = useInputPreview()

    await open('external_data', 'server')

    expect(PREVIEW_ROWS).toBe(100)
    expect(getExternalDataPreview).toHaveBeenCalledWith(100)
    expect(csv.value).toEqual(data)
  })

  it('previews a selected config file without calling the server', async () => {
    const { open, config, current } = useInputPreview()

    await open('config', fakeFile('{"b": 2}'))

    expect(config.value).toEqual({ b: 2 })
    expect(current.value?.source).toBe('local')
    expect(getConfigPreview).not.toHaveBeenCalled()
  })

  it('reports a selected config that is not a JSON object', async () => {
    const { open, config, error } = useInputPreview()

    await open('config', fakeFile('[1]'))

    expect(config.value).toBeNull()
    expect(error.value).toBe('config.json must be a JSON object')
  })

  it('previews a selected CSV by streaming it', async () => {
    const { open, csv } = useInputPreview()

    await open('external_data', fakeFile('orgUnit,period\nA,202401\n'))

    expect(csv.value?.rows).toEqual([['A', '202401']])
    expect(getExternalDataPreview).not.toHaveBeenCalled()
  })

  it('shows the backend detail on error', async () => {
    getConfigPreview.mockRejectedValue({ response: { data: { detail: 'config is not in input/' } } })
    const { open, error, loading } = useInputPreview()

    await open('config', 'server')

    expect(error.value).toBe('config is not in input/')
    expect(loading.value).toBe(false)
  })

  it('ignores a slow answer once another preview was opened', async () => {
    let resolveFirst: (v: unknown) => void = () => {}
    getConfigPreview.mockReturnValueOnce(new Promise(r => (resolveFirst = r)))
    const { open, config, current } = useInputPreview()

    const first = open('config', 'server')
    await open('config', fakeFile('{"new": true}'))
    resolveFirst({ old: true })
    await first

    expect(current.value?.source).toBe('local')
    expect(config.value).toEqual({ new: true })
  })

  it('close() clears everything', async () => {
    getConfigPreview.mockResolvedValue({ a: 1 })
    const { open, close, current, config } = useInputPreview()
    await open('config', 'server')

    close()

    expect(current.value).toBeNull()
    expect(config.value).toBeNull()
  })
})

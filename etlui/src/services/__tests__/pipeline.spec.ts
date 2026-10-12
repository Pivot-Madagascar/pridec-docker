import { describe, it, expect, vi, beforeEach } from 'vitest'

const post = vi.fn()
const get = vi.fn()
const put = vi.fn()
const del = vi.fn()
vi.mock('@/services/api', async importOriginal => ({
  ...(await importOriginal<object>()),
  default: {
    post: (...args: unknown[]) => post(...args),
    get: (...args: unknown[]) => get(...args),
    put: (...args: unknown[]) => put(...args),
    delete: (...args: unknown[]) => del(...args)
  }
}))

import * as pipeline from '@/services/pipeline'
import { uploadInputFile, deleteInputFile } from '@/services/inputs'

const CONFIRM = { params: { confirm: true } }

describe('pipeline service', () => {
  beforeEach(() => vi.clearAllMocks())

  it('reads the state from GET /pipeline/checkpoints', async () => {
    get.mockResolvedValue({ data: { cycle: '202610' } })

    expect(await pipeline.getCheckpoints()).toEqual({ cycle: '202610' })
    expect(get).toHaveBeenCalledWith('/pipeline/checkpoints')
  })

  it('launches a job on its own route, with confirm only when asked', async () => {
    post.mockResolvedValue({ data: { job_id: 'import_gee_1' } })

    expect(await pipeline.launchJob('import_gee')).toBe('import_gee_1')
    await pipeline.launchJob('import_gee', true)

    expect(post).toHaveBeenNthCalledWith(1, '/import_gee', undefined, undefined)
    expect(post).toHaveBeenNthCalledWith(2, '/import_gee', undefined, CONFIRM)
  })

  it('launches the forecast on /forecast/ with the etlhub default paths', async () => {
    post.mockResolvedValue({ data: { job_id: 'forecast_1' } })

    await pipeline.launchJob('forecast')

    expect(post).toHaveBeenCalledWith('/forecast/', {}, undefined)
  })

  it('returns null for a synchronous job without job_id', async () => {
    post.mockResolvedValue({ data: { status: 'success' } })

    expect(await pipeline.launchJob('update_key')).toBeNull()
  })

  it('opens, decides and abandons the forecast run', async () => {
    post.mockResolvedValue({ data: {} })
    del.mockResolvedValue({ data: { abandoned: 'CSB/Malaria' } })

    await pipeline.openRun('CSB', 'Malaria', true)
    await pipeline.decideRun('reject')

    expect(post).toHaveBeenNthCalledWith(1, '/pipeline/runs', { source: 'CSB', disease: 'Malaria' }, CONFIRM)
    expect(post).toHaveBeenNthCalledWith(2, '/pipeline/runs/current/approve', { decision: 'reject' })
    expect(await pipeline.abandonRun()).toBe('CSB/Malaria')
    expect(del).toHaveBeenCalledWith('/pipeline/runs/current')
  })

  it('switches the mode with PUT /pipeline/mode', async () => {
    put.mockResolvedValue({ data: { dry_run: false } })

    expect(await pipeline.setMode(false, true)).toBe(false)
    expect(put).toHaveBeenCalledWith('/pipeline/mode', { dry_run: false }, CONFIRM)
  })

  it('releases the lock with DELETE /pipeline/lock', async () => {
    del.mockResolvedValue({ data: { released: 'dead_job' } })

    expect(await pipeline.releaseLock()).toBe('dead_job')
    expect(del).toHaveBeenCalledWith('/pipeline/lock')
  })
})

describe('input files with confirmation', () => {
  beforeEach(() => vi.clearAllMocks())

  it('adds confirm=true to the upload only when confirmed', async () => {
    post.mockResolvedValue({ data: { saved: 'input/config.json' } })

    await uploadInputFile('config', new File(['{}'], 'c.json'), true)

    expect(post.mock.calls[0][2]).toEqual({ headers: { 'Content-Type': 'multipart/form-data' }, params: { confirm: true } })
  })

  it('adds confirm=true to the delete only when confirmed', async () => {
    del.mockResolvedValue({ data: { deleted: 'input/config.json' } })

    await deleteInputFile('config', true)

    expect(del).toHaveBeenCalledWith('/input/files/config', CONFIRM)
  })
})

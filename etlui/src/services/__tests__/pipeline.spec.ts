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
    delete: (...args: unknown[]) => del(...args),
    getUri: ({ url }: { url: string }) => `http://localhost:8111${url}`
  }
}))

import * as pipeline from '@/services/pipeline'
import { uploadInputFile, deleteInputFile } from '@/services/inputs'

const CONFIRM = { params: { confirm: true } }

describe('pipeline service', () => {
  beforeEach(() => vi.clearAllMocks())

  it('reads the import availability report from GET /import_availability', async () => {
    get.mockResolvedValue({ data: { imports: [] } })

    expect(await pipeline.getImportAvailability()).toEqual({ imports: [] })
    expect(get).toHaveBeenCalledWith('/import_availability', undefined)
    await pipeline.getImportAvailability(true) // Refresh: etlhub asks DHIS2 for every section
    expect(get).toHaveBeenLastCalledWith('/import_availability', { params: { refresh: true } })
  })

  it('reads the fetched Pivot data, sends the chosen elements in the approve body, confirm in the query, and returns the approval job', async () => {
    get.mockResolvedValue({ data: { imports: [{ task: 'import_pivot_com', elements: [] }] } })
    expect(await pipeline.getFetchedImports()).toEqual([{ task: 'import_pivot_com', elements: [] }])
    expect(get).toHaveBeenCalledWith('/pipeline/imports/fetched')

    // approve: 202 with the approve_imports job (a Celery job since 2026-11-27), followed like any launch
    post.mockResolvedValue({ data: { status: 'accepted', job_id: 'approve_imports_1a2b3c4d' } })
    const approval = await pipeline.decideImports('approve', ['pridec_historic_CSBMalaria'], true)
    expect(approval.jobId).toBe('approve_imports_1a2b3c4d')
    expect(post).toHaveBeenLastCalledWith('/pipeline/imports/approve',
      { decision: 'approve', elements: ['pridec_historic_CSBMalaria'] }, { ...CONFIRM, headers: { 'X-Request-ID': approval.requestId } })
    post.mockResolvedValue({ data: { decision: 'reject' } }) // reject: 200, no job
    expect((await pipeline.decideImports('reject')).jobId).toBeNull()
    expect(post).toHaveBeenLastCalledWith('/pipeline/imports/approve', { decision: 'reject' },
      { params: {}, headers: { 'X-Request-ID': expect.any(String) } })
  })

  it('reads the state from GET /pipeline/checkpoints', async () => {
    get.mockResolvedValue({ data: { cycle: '202610' } })

    expect(await pipeline.getCheckpoints()).toEqual({ cycle: '202610' })
    expect(get).toHaveBeenCalledWith('/pipeline/checkpoints')
  })

  it('launches a job on its own route, with confirm only when asked', async () => {
    post.mockResolvedValue({ data: { job_id: 'import_gee_1' } })

    const { jobId, requestId } = await pipeline.launchJob('import_gee')
    await pipeline.launchJob('import_gee', true)

    expect(jobId).toBe('import_gee_1')
    // etlhub tracks the request under this X-Request-ID: RecentActivity finds it back with it
    expect(post).toHaveBeenNthCalledWith(1, '/import_gee', undefined, { params: {}, headers: { 'X-Request-ID': requestId } })
    expect(post).toHaveBeenNthCalledWith(2, '/import_gee', undefined, { ...CONFIRM, headers: { 'X-Request-ID': expect.any(String) } })
  })

  it('launches the forecast on /forecast/ with the etlhub default paths', async () => {
    post.mockResolvedValue({ data: { job_id: 'forecast_1' } })

    await pipeline.launchJob('forecast')

    expect(post).toHaveBeenCalledWith('/forecast/', {}, { params: {}, headers: { 'X-Request-ID': expect.any(String) } })
  })

  it('launches update_key as a background job (202 with a job_id since 2026-11-27)', async () => {
    post.mockResolvedValue({ data: { status: 'accepted', job_id: 'update_key_1' } })

    expect((await pipeline.launchJob('update_key')).jobId).toBe('update_key_1')
  })

  it('opens, decides and abandons the forecast run', async () => {
    post.mockResolvedValue({ data: {} })
    del.mockResolvedValue({ data: { abandoned: 'CSB/Malaria' } })

    await pipeline.openRun('CSB', 'Malaria', true)
    await pipeline.decideRun('reject')
    await pipeline.skipAlerts()

    expect(post).toHaveBeenNthCalledWith(1, '/pipeline/runs', { source: 'CSB', disease: 'Malaria' }, CONFIRM)
    expect(post).toHaveBeenNthCalledWith(2, '/pipeline/runs/current/approve', { decision: 'reject' })
    expect(post).toHaveBeenNthCalledWith(3, '/pipeline/runs/current/skip_alerts')
    expect(await pipeline.abandonRun()).toBe('CSB/Malaria')
    expect(del).toHaveBeenCalledWith('/pipeline/runs/current')
  })

  it('switches the mode with PUT /pipeline/mode', async () => {
    put.mockResolvedValue({ data: { test_mode: false } })

    expect(await pipeline.setMode(false)).toBe(false)
    expect(put).toHaveBeenCalledWith('/pipeline/mode', { test_mode: false, pass_action: null })
    await pipeline.setMode(true, 'abandon') // the user's choice for the active pass of the mode left
    expect(put).toHaveBeenLastCalledWith('/pipeline/mode', { test_mode: true, pass_action: 'abandon' })
  })

  it('chooses the cycle with PUT /pipeline/cycle, null for the current month', async () => {
    put.mockResolvedValue({})

    await pipeline.setCycle('202609')
    await pipeline.setCycle(null)
    expect(put).toHaveBeenNthCalledWith(1, '/pipeline/cycle', { cycle: '202609' })
    expect(put).toHaveBeenNthCalledWith(2, '/pipeline/cycle', { cycle: null })
  })

  it('releases the lock with DELETE /pipeline/lock', async () => {
    del.mockResolvedValue({ data: { released: 'dead_job' } })

    expect(await pipeline.releaseLock()).toBe('dead_job')
    expect(del).toHaveBeenCalledWith('/pipeline/lock', undefined)

    await pipeline.releaseLock(true) // the user confirmed etlhub's 409: the job may still run
    expect(del).toHaveBeenLastCalledWith('/pipeline/lock', { params: { confirm: true } })
  })
})

describe('cycle journal', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists the cycles', async () => {
    get.mockResolvedValue({ data: [{ cycle: '202610' }] })

    expect(await pipeline.getCycles()).toEqual([{ cycle: '202610' }])
    expect(get).toHaveBeenCalledWith('/pipeline/cycles')
  })

  it('reads the journal of a pass and builds the CSV link', async () => {
    get.mockResolvedValue({ data: [{ event: 'launched' }] })

    expect(await pipeline.getJournal('3f9c1a2b')).toEqual([{ event: 'launched' }])
    expect(get).toHaveBeenCalledWith('/pipeline/passes/3f9c1a2b/journal')
    expect(pipeline.journalCsvUrl('3f9c1a2b')).toBe('http://localhost:8111/pipeline/passes/3f9c1a2b/journal.csv')
    expect(pipeline.archiveUrl('input')).toBe('http://localhost:8111/output/archive?folder=input') // the open run's input/ only
    expect(pipeline.archiveUrl('output')).toBe('http://localhost:8111/output/archive?folder=output')
  })

  it('pauses the active pass, resumes or abandons one by its id', async () => {
    post.mockResolvedValue({ data: { id: '3f9c1a2b', state: 'paused' } })

    await pipeline.pausePass()
    await pipeline.resumePass('3f9c1a2b')
    await pipeline.abandonPass('3f9c1a2b')

    expect(post.mock.calls).toEqual([
      ['/pipeline/passes/current/pause'], ['/pipeline/passes/3f9c1a2b/resume'], ['/pipeline/passes/3f9c1a2b/abandon']])
  })

  it('starts a pass with an empty body (GEE variables: chosen in Import GEE; no DRYRUN: the mode decides), confirm in the query', async () => {
    post.mockResolvedValue({ data: { id: '3f9c1a2b', state: 'active' } })

    await pipeline.startPass(true)

    expect(post).toHaveBeenCalledWith('/pipeline/passes', {}, { params: { confirm: true } })
  })

  it('launches Import GEE with the chosen variables in the body, and reads the import state of each variable', async () => {
    post.mockResolvedValue({ data: { job_id: 'import_gee_1' } })
    const variables = [{ variable: 'v1', chosen: true, state: null }]
    get.mockResolvedValue({ data: { variables } })

    await pipeline.launchJob('import_gee', true, { gee_variables: ['v1', 'v3'] })

    expect(post).toHaveBeenCalledWith('/import_gee', { gee_variables: ['v1', 'v3'] },
      { params: { confirm: true }, headers: { 'X-Request-ID': expect.any(String) } })
    expect(await pipeline.getGeeImports()).toEqual(variables)
    expect(get).toHaveBeenCalledWith('/pipeline/imports/gee')
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

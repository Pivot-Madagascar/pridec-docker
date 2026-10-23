// Badge colours of an HTTP status code or a job status ('success', 'running', ...).
export function statusColor(status: number | string | null | undefined): string {
  if (status === 'success' || (typeof status === 'number' && status >= 200 && status < 300)) return 'bg-green-900 text-green-300'
  if (status === 'error' || (typeof status === 'number' && status >= 500)) return 'bg-red-900 text-red-300'
  if (typeof status === 'number' && status >= 400) return 'bg-yellow-900 text-yellow-300'
  if (status === 'running' || status === 'pending') return 'bg-blue-900 text-blue-300'
  return 'bg-gray-700 text-gray-300'
}

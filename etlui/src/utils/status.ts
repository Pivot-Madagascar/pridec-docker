// Badge colours of an HTTP status code or a job status ('success', 'running', ...).
export function statusColor(status: number | string | null | undefined): string {
  if (status === 'success' || (typeof status === 'number' && status >= 200 && status < 300)) return 'bg-success/15 text-success'
  if (status === 'error' || (typeof status === 'number' && status >= 500)) return 'bg-destructive/15 text-destructive'
  if (typeof status === 'number' && status >= 400) return 'bg-warning/15 text-warning'
  if (status === 'running' || status === 'pending') return 'bg-primary/15 text-primary'
  return 'bg-muted text-muted-foreground'
}

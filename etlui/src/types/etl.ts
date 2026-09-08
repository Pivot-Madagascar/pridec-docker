export interface ActivityEntry {
  id: number
  action: string
  message: string
  time: string
  success: boolean
  jobId?: string
}
import api from './api'
import type { ConfigResponse } from '@/types/config'

export const configService = {
  async get(): Promise<ConfigResponse> {
    const { data } = await api.get<ConfigResponse>('/api/config')
    return data
  },
  async update(payload: Partial<ConfigResponse>): Promise<ConfigResponse> {
    const { data } = await api.put<ConfigResponse>('/api/config', payload)
    return data
  },
  async reload(): Promise<ConfigResponse> {
    const { data } = await api.put<ConfigResponse>('/api/config/reload')
    return data
  }
}
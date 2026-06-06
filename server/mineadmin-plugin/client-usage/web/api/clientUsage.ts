import request from '@/utils/request'

export interface ClientUsageRecord {
  id: number
  username: string
  client_id: string
  client_platform: string
  client_version: string
  event_type: string
  event_detail: string
  ip_address?: string
  created_at: string
}

export interface ClientUsageListResult {
  list: ClientUsageRecord[]
  total: number
  page: number
  pageSize: number
}

export function getClientUsageList(params: Record<string, unknown>) {
  return request<{ data: ClientUsageListResult }>({
    url: '/admin/app/clientUsage/list',
    method: 'get',
    params,
  })
}

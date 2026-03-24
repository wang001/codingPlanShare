import request from './axios'
import type { PointsBalance, PointsLog, PaginationParams } from '../types'

export function getBalance(): Promise<PointsBalance> {
  return request.get<PointsBalance>('/api/v1/points').then(r => r.data)
}

export function getPointsLogs(params?: PaginationParams): Promise<PointsLog[]> {
  return request.get<PointsLog[]>('/api/v1/points/logs', { params }).then(r => r.data)
}

import request from './axios'
import type { User, Key, AdminLog, PaginationParams } from '../types'

// 用户管理
export function adminGetUsers(): Promise<User[]> {
  return request.get<User[]>('/api/admin/users').then(r => r.data)
}

export function adminCreateUser(payload: {
  username: string
  email: string
  password: string
}): Promise<User> {
  return request.post<User>('/api/admin/users', payload).then(r => r.data)
}

export function adminUpdateUserStatus(id: number, status: 0 | 1): Promise<User> {
  return request.put<User>(`/api/admin/users/${id}`, null, { params: { status } }).then(r => r.data)
}

// 积分管理
export function adminAdjustPoints(payload: {
  user_id: number
  amount: number
  remark: string
}): Promise<void> {
  return request.post('/api/admin/points', payload).then(() => undefined)
}

// 密钥管理
export function adminGetKeys(): Promise<Key[]> {
  return request.get<Key[]>('/api/admin/keys').then(r => r.data)
}

export function adminUpdateKeyStatus(id: number, status: 0 | 1 | 2 | 3 | 4): Promise<Key> {
  return request.put<Key>(`/api/admin/keys/${id}`, null, { params: { status } }).then(r => r.data)
}

export function adminDeleteKey(id: number): Promise<void> {
  return request.delete(`/api/admin/keys/${id}`).then(() => undefined)
}

// 调用日志
export function adminGetLogs(params?: PaginationParams): Promise<AdminLog[]> {
  return request.get<AdminLog[]>('/api/admin/logs', { params }).then(r => r.data)
}

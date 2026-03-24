import request from './axios'
import type { Key, CreateKeyPayload } from '../types'

export function getKeys(): Promise<Key[]> {
  return request.get<Key[]>('/api/v1/keys').then(r => r.data)
}

export function createKey(payload: CreateKeyPayload): Promise<Key> {
  return request.post<Key>('/api/v1/keys', payload).then(r => r.data)
}

export function updateKey(id: number, payload: { name?: string; status?: number }): Promise<Key> {
  return request.put<Key>(`/api/v1/keys/${id}`, payload).then(r => r.data)
}

export function deleteKey(id: number): Promise<void> {
  return request.delete(`/api/v1/keys/${id}`).then(() => undefined)
}

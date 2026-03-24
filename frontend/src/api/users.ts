import request from './axios'
import type { User } from '../types'

export function getMe(): Promise<User> {
  return request.get<User>('/api/v1/users/me').then(r => r.data)
}

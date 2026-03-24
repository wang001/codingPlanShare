import request from './axios'
import type { LoginResponse } from '../types'

export function userLogin(email: string, password: string): Promise<LoginResponse> {
  return request.post<LoginResponse>('/api/v1/auth/login', { email, password }).then(r => r.data)
}

export function adminLogin(password: string): Promise<LoginResponse> {
  return request.post<LoginResponse>('/api/v1/auth/admin/login', { password }).then(r => r.data)
}

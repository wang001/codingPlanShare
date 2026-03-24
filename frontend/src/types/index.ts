// 认证相关
export interface LoginResponse {
  access_token: string
  token_type: string
  user_id?: number
  username?: string
}

// 用户相关
export interface User {
  id: number
  username: string
  email: string
  balance: number
  status: number
  created_at: string
}

// 积分相关
export interface PointsBalance {
  balance: number
}

export interface PointsLog {
  id: number
  user_id: number
  amount: number
  type: number // 1=调用消耗, 2=托管收益, 3=管理员调整, 4=平台收入
  related_key_id: number | null
  model: string | null
  remark: string | null
  created_at: string
}

// 密钥相关
export interface Key {
  id: number
  user_id: number
  key_type: number // 1=平台调用密钥, 2=厂商托管密钥
  provider: string | null
  name: string
  status: number // 0=正常, 1=删除, 2=禁用, 3=超限, 4=无效
  used_count: number
  last_used_at: string | null
  created_at: string
  encrypted_key?: string
}

export type KeyProvider = 'zhipu' | 'minimax' | 'alibaba' | 'tencent' | 'baidu'

export interface CreateKeyPayload {
  name: string
  key_type: 1 | 2
  provider?: KeyProvider
  encrypted_key?: string
}

// 管理员调用日志
export interface AdminLog {
  id: number
  user_id: number
  model: string | null
  status: number         // 0=失败, 1=成功
  provider_key_id: number | null
  error_msg: string | null
  ip: string | null
  created_at: string
}

// 分页
export interface PaginationParams {
  limit?: number
  offset?: number
}

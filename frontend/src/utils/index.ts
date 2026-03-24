import dayjs from 'dayjs'

// 秒级时间戳转可读时间
export function formatTimestamp(ts: string | number | null | undefined): string {
  if (!ts) return '-'
  // 如果是字符串形式的ISO时间，直接用dayjs解析
  // 如果是纯数字，判断是秒还是毫秒
  const num = typeof ts === 'string' ? Date.parse(ts) : ts
  if (isNaN(num)) return '-'
  // 如果是秒级时间戳（小于 2e10），乘以1000
  if (typeof ts === 'number' && ts < 2e10) {
    return dayjs(ts * 1000).format('YYYY-MM-DD HH:mm:ss')
  }
  return dayjs(num).format('YYYY-MM-DD HH:mm:ss')
}

// 积分类型中文映射
export function getPointsTypeLabel(type: number): string {
  const map: Record<number, string> = {
    1: '调用消耗',
    2: '托管收益',
    3: '管理员调整',
    4: '平台收入',
  }
  return map[type] || `类型${type}`
}

// 密钥类型中文映射
export function getKeyTypeLabel(keyType: number): string {
  const map: Record<number, string> = {
    1: '平台调用密钥',
    2: '厂商托管密钥',
  }
  return map[keyType] || `类型${keyType}`
}

// 密钥状态中文映射
export function getKeyStatusLabel(status: number): string {
  const map: Record<number, string> = {
    0: '正常',
    1: '已删除',
    2: '已禁用',
    3: '超出限额',
    4: '无效',
  }
  return map[status] || `状态${status}`
}

// 密钥状态颜色
export function getKeyStatusColor(status: number): string {
  const map: Record<number, string> = {
    0: 'success',
    1: 'default',
    2: 'warning',
    3: 'error',
    4: 'error',
  }
  return map[status] || 'default'
}

// 用户状态中文映射（后端：0=禁用，1=正常）
export function getUserStatusLabel(status: number): string {
  const map: Record<number, string> = {
    0: '已禁用',
    1: '正常',
  }
  return map[status] || `状态${status}`
}

// 厂商名称映射
export function getProviderLabel(provider: string | null): string {
  if (!provider) return '-'
  const map: Record<string, string> = {
    zhipu: '智谱',
    minimax: 'MiniMax',
    alibaba: '阿里云',
    tencent: '腾讯云',
    baidu: '百度',
  }
  return map[provider] || provider
}

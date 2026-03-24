import axios from 'axios'
import { message } from 'antd'

const request = axios.create({
  timeout: 30000,
})

// 请求拦截器：自动带上 Authorization header
request.interceptors.request.use(
  (config) => {
    // 判断是管理员路由还是普通用户路由
    const url = config.url || ''
    if (url.startsWith('/admin')) {
      const adminToken = localStorage.getItem('admin_token')
      if (adminToken) {
        config.headers.Authorization = `Bearer ${adminToken}`
      }
    } else {
      const token = localStorage.getItem('user_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理 401 跳转登录
request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      if (url.startsWith('/admin')) {
        localStorage.removeItem('admin_token')
        window.location.href = '/login'
        message.error('管理员会话已过期，请重新登录')
      } else {
        localStorage.removeItem('user_token')
        localStorage.removeItem('user_info')
        window.location.href = '/login'
        message.error('登录已过期，请重新登录')
      }
    } else if (error.response?.status === 403) {
      message.error('权限不足')
    } else if (error.response?.data?.detail) {
      message.error(error.response.data.detail)
    } else if (error.message === 'Network Error') {
      message.error('网络错误，请检查连接')
    }
    return Promise.reject(error)
  }
)

export default request

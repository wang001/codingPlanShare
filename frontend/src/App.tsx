import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'

// 布局
import UserLayout from './layouts/UserLayout'
import AdminLayout from './layouts/AdminLayout'

// 页面
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import PointsPage from './pages/PointsPage'
import KeysPage from './pages/KeysPage'
import StatsPage from './pages/StatsPage'

// 管理员页面
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminKeys from './pages/admin/AdminKeys'
import AdminLogs from './pages/admin/AdminLogs'

// 权限守卫：用户端
function UserGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('user_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

// 权限守卫：管理员端
function AdminGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('admin_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AntdApp>
        <Router>
          <Routes>
            {/* 登录页 */}
            <Route path="/login" element={<LoginPage />} />

            {/* 用户端路由 */}
            <Route
              element={
                <UserGuard>
                  <UserLayout />
                </UserGuard>
              }
            >
              <Route path="/" element={<HomePage />} />
              <Route path="/points" element={<PointsPage />} />
              <Route path="/keys" element={<KeysPage />} />
              <Route path="/stats" element={<StatsPage />} />
            </Route>

            {/* 管理员端路由 */}
            <Route
              path="/admin"
              element={
                <AdminGuard>
                  <AdminLayout />
                </AdminGuard>
              }
            >
              <Route index element={<AdminDashboard />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="keys" element={<AdminKeys />} />
              <Route path="logs" element={<AdminLogs />} />
            </Route>

            {/* 兜底重定向 */}
            <Route
              path="*"
              element={
                <Navigate
                  to={
                    localStorage.getItem('admin_token')
                      ? '/admin'
                      : localStorage.getItem('user_token')
                        ? '/'
                        : '/login'
                  }
                  replace
                />
              }
            />
          </Routes>
        </Router>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App

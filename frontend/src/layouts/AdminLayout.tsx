import React, { useState } from 'react'
import { Layout, Menu, Button, Typography, Drawer, theme, Tag } from 'antd'
import {
  DashboardOutlined,
  TeamOutlined,
  KeyOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MenuOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/admin', icon: <DashboardOutlined />, label: '控制台' },
  { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
  { key: '/admin/keys', icon: <KeyOutlined />, label: '密钥管理' },
  { key: '/admin/logs', icon: <FileTextOutlined />, label: '调用日志' },
]

const AdminLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { token } = theme.useToken()

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    navigate('/login')
  }

  const handleMenuClick = (key: string) => {
    navigate(key)
    setDrawerOpen(false)
  }

  const selectedKey = menuItems.find(item => item.key === location.pathname)?.key || '/admin'

  const siderMenu = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '20px 16px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SafetyOutlined style={{ fontSize: 24, color: token.colorWarning }} />
          <div>
            <div style={{ fontWeight: 600, color: token.colorText, fontSize: 14 }}>
              管理员控制台
            </div>
            <Tag color="gold" style={{ marginTop: 2 }}>Admin</Tag>
          </div>
        </div>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
        style={{ flex: 1, borderRight: 'none' }}
      />
      <div style={{ padding: '12px 16px', borderTop: `1px solid ${token.colorBorderSecondary}` }}>
        <Button
          icon={<LogoutOutlined />}
          onClick={handleLogout}
          block
          type="text"
          danger
        >
          退出登录
        </Button>
      </div>
    </div>
  )

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 桌面端侧边栏 */}
      <Sider
        width={220}
        style={{
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          display: 'none',
        }}
        className="admin-desktop-sider"
      >
        <div style={{ height: 48, display: 'flex', alignItems: 'center', padding: '0 16px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <Text strong style={{ fontSize: 16 }}>LLM 路由管理</Text>
        </div>
        {siderMenu}
      </Sider>

      <Layout>
        {/* 顶部导航（移动端） */}
        <Header
          style={{
            background: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            padding: '0 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 56,
            lineHeight: '56px',
          }}
          className="admin-mobile-header"
        >
          <Text strong style={{ fontSize: 16 }}>管理员控制台</Text>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setDrawerOpen(true)}
          />
        </Header>

        {/* 移动端 Drawer */}
        <Drawer
          placement="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          width={240}
          bodyStyle={{ padding: 0 }}
          headerStyle={{ display: 'none' }}
        >
          {siderMenu}
        </Drawer>

        <Content
          style={{
            padding: 16,
            background: token.colorBgLayout,
            minHeight: 'calc(100vh - 56px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>

      <style>{`
        @media (min-width: 768px) {
          .admin-desktop-sider {
            display: flex !important;
          }
          .admin-mobile-header {
            display: none !important;
          }
        }
      `}</style>
    </Layout>
  )
}

export default AdminLayout

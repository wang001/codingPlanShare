import React, { useState } from 'react'
import { Layout, Menu, Button, Avatar, Typography, Drawer, theme } from 'antd'
import {
  HomeOutlined,
  WalletOutlined,
  KeyOutlined,
  BarChartOutlined,
  LogoutOutlined,
  MenuOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: '首页' },
  { key: '/points', icon: <WalletOutlined />, label: '积分' },
  { key: '/keys', icon: <KeyOutlined />, label: '密钥' },
  { key: '/stats', icon: <BarChartOutlined />, label: '统计' },
]

const UserLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { token } = theme.useToken()

  const userInfo = (() => {
    try {
      return JSON.parse(localStorage.getItem('user_info') || '{}')
    } catch {
      return {}
    }
  })()

  const handleLogout = () => {
    localStorage.removeItem('user_token')
    localStorage.removeItem('user_info')
    navigate('/login')
  }

  const handleMenuClick = (key: string) => {
    navigate(key)
    setDrawerOpen(false)
  }

  const selectedKey = menuItems.find(item => item.key === location.pathname)?.key || '/'

  const siderMenu = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '20px 16px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: token.colorPrimary }} />
          <div>
            <div style={{ fontWeight: 600, color: token.colorText, fontSize: 14 }}>
              {userInfo.username || '用户'}
            </div>
            <div style={{ color: token.colorTextSecondary, fontSize: 12 }}>
              {userInfo.email || ''}
            </div>
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
        className="desktop-sider"
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
          className="mobile-header"
        >
          <Text strong style={{ fontSize: 16 }}>LLM 路由管理</Text>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setDrawerOpen(true)}
            className="mobile-menu-btn"
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
          .desktop-sider {
            display: flex !important;
          }
          .mobile-header {
            display: none !important;
          }
          .mobile-menu-btn {
            display: none !important;
          }
        }
      `}</style>
    </Layout>
  )
}

export default UserLayout

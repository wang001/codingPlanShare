import React, { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Tabs, Typography, Space, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, SafetyOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { userLogin, adminLogin } from '../api/auth'

const { Title, Text } = Typography

const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('user')
  const [loading, setLoading] = useState(false)
  const [userForm] = Form.useForm()
  const [adminForm] = Form.useForm()

  useEffect(() => {
    const userToken = localStorage.getItem('user_token')
    const adminToken = localStorage.getItem('admin_token')
    if (userToken) navigate('/')
    else if (adminToken) navigate('/admin')
  }, [navigate])

  const handleUserLogin = async (values: { email: string; password: string }) => {
    setLoading(true)
    try {
      const data = await userLogin(values.email, values.password)
      localStorage.setItem('user_token', data.access_token)
      localStorage.setItem(
        'user_info',
        JSON.stringify({ username: data.username, user_id: data.user_id })
      )
      message.success('登录成功')
      navigate('/')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(detail || '登录失败，请检查邮箱和密码')
    } finally {
      setLoading(false)
    }
  }

  const handleAdminLogin = async (values: { password: string }) => {
    setLoading(true)
    try {
      const data = await adminLogin(values.password)
      localStorage.setItem('admin_token', data.access_token)
      message.success('管理员登录成功')
      navigate('/admin')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(detail || '管理员密码错误')
    } finally {
      setLoading(false)
    }
  }

  const tabItems = [
    {
      key: 'user',
      label: (
        <Space>
          <UserOutlined />
          用户登录
        </Space>
      ),
      children: (
        <Form
          form={userForm}
          onFinish={handleUserLogin}
          layout="vertical"
          size="large"
          autoComplete="off"
        >
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱格式' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'admin',
      label: (
        <Space>
          <SafetyOutlined />
          管理员登录
        </Space>
      ),
      children: (
        <Form
          form={adminForm}
          onFinish={handleAdminLogin}
          layout="vertical"
          size="large"
          autoComplete="off"
        >
          <Form.Item
            name="password"
            label="管理员密码"
            rules={[{ required: true, message: '请输入管理员密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入管理员密码" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={loading} danger>
              管理员登录
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ]

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 16,
      }}
    >
      <Card
        style={{ width: '100%', maxWidth: 420, borderRadius: 12 }}
        styles={{ body: { padding: '32px 32px 24px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Title level={3} style={{ margin: 0 }}>
            LLM 路由管理
          </Title>
          <Text type="secondary">API 聚合计费路由器</Text>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          centered
        />
      </Card>
    </div>
  )
}

export default LoginPage

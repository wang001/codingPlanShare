import React, { useEffect, useState } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Button,
  Space,
  Spin,
  message,
} from 'antd'
import {
  WalletOutlined,
  KeyOutlined,
  BarChartOutlined,
  ArrowRightOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getMe } from '../api/users'
import type { User } from '../types'

const { Title, Text, Paragraph } = Typography

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then((data) => {
        setUser(data)
        // 更新本地缓存的用户信息
        const existing = (() => {
          try { return JSON.parse(localStorage.getItem('user_info') || '{}') } catch { return {} }
        })()
        localStorage.setItem('user_info', JSON.stringify({ ...existing, username: data.username, email: data.email }))
      })
      .catch(() => {
        message.error('获取用户信息失败')
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card style={{ marginBottom: 16, borderRadius: 8 }}>
        <Space align="center">
          <UserOutlined style={{ fontSize: 32, color: '#1677ff' }} />
          <div>
            <Title level={4} style={{ margin: 0 }}>
              欢迎回来，{user?.username || '用户'}
            </Title>
            <Text type="secondary">{user?.email}</Text>
          </div>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <Card
            hoverable
            style={{ borderRadius: 8, cursor: 'pointer' }}
            onClick={() => navigate('/points')}
          >
            <Statistic
              title="积分余额"
              value={user?.balance ?? 0}
              prefix={<WalletOutlined />}
              suffix="分"
              valueStyle={{ color: '#1677ff' }}
            />
            <div style={{ marginTop: 12 }}>
              <Button type="link" style={{ padding: 0 }} icon={<ArrowRightOutlined />}>
                查看积分明细
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card
            hoverable
            style={{ borderRadius: 8, cursor: 'pointer' }}
            onClick={() => navigate('/keys')}
          >
            <Statistic
              title="API 密钥"
              value="管理密钥"
              prefix={<KeyOutlined />}
              valueStyle={{ fontSize: 20 }}
            />
            <div style={{ marginTop: 12 }}>
              <Button type="link" style={{ padding: 0 }} icon={<ArrowRightOutlined />}>
                管理 API 密钥
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card
            hoverable
            style={{ borderRadius: 8, cursor: 'pointer' }}
            onClick={() => navigate('/stats')}
          >
            <Statistic
              title="调用统计"
              value="查看统计"
              prefix={<BarChartOutlined />}
              valueStyle={{ fontSize: 20 }}
            />
            <div style={{ marginTop: 12 }}>
              <Button type="link" style={{ padding: 0 }} icon={<ArrowRightOutlined />}>
                查看调用记录
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16, borderRadius: 8 }}>
        <Title level={5}>使用说明</Title>
        <Paragraph type="secondary" style={{ margin: 0 }}>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            <li>通过平台 API 密钥调用 LLM 模型，每次调用会扣除相应积分</li>
            <li>托管厂商密钥（智谱、MiniMax、阿里云等）可获得托管收益积分</li>
            <li>在密钥管理页面创建和管理平台密钥及厂商密钥</li>
            <li>在积分页面查看余额及详细的收支明细</li>
          </ul>
        </Paragraph>
      </Card>
    </div>
  )
}

export default HomePage

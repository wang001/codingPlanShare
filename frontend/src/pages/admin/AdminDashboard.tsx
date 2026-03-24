import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Spin, message } from 'antd'
import {
  TeamOutlined,
  KeyOutlined,
  FileTextOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { adminGetUsers, adminGetKeys, adminGetLogs } from '../../api/admin'

const AdminDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalKeys: 0,
    activeKeys: 0,
    totalLogs: 0,
  })

  useEffect(() => {
    Promise.all([
      adminGetUsers().catch(() => []),
      adminGetKeys().catch(() => []),
      adminGetLogs({ limit: 1, offset: 0 }).catch(() => []),
    ])
      .then(([users, keys]) => {
        setStats({
          totalUsers: users.length,
          activeUsers: users.filter((u: any) => u.status === 0).length,
          totalKeys: keys.length,
          activeKeys: keys.filter((k: any) => k.status === 0).length,
          totalLogs: 0,
        })
      })
      .catch(() => {
        message.error('获取概览数据失败')
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <SafetyOutlined style={{ fontSize: 28, color: '#faad14' }} />
          <div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>管理员控制台</div>
            <div style={{ color: '#999', fontSize: 13 }}>LLM API 聚合计费路由器管理后台</div>
          </div>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="总用户数"
              value={stats.totalUsers}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="正常用户"
              value={stats.activeUsers}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="总密钥数"
              value={stats.totalKeys}
              prefix={<KeyOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="正常密钥"
              value={stats.activeKeys}
              prefix={<KeyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={8}>
          <Card
            hoverable
            style={{ borderRadius: 8 }}
          >
            <Statistic
              title="快捷入口：用户管理"
              value="管理用户"
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            hoverable
            style={{ borderRadius: 8 }}
          >
            <Statistic
              title="快捷入口：密钥管理"
              value="管理密钥"
              prefix={<KeyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            hoverable
            style={{ borderRadius: 8 }}
          >
            <Statistic
              title="快捷入口：调用日志"
              value="查看日志"
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default AdminDashboard

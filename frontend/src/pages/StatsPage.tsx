import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Typography,
  Statistic,
  Row,
  Col,
  Spin,
  message,
  Button,
} from 'antd'
import { BarChartOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { getPointsLogs } from '../api/points'
import type { PointsLog } from '../types'
import { formatTimestamp, getPointsTypeLabel } from '../utils'

const { Title } = Typography

const PAGE_SIZE = 50

const StatsPage: React.FC = () => {
  const [logs, setLogs] = useState<PointsLog[]>([])
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [tableLoading, setTableLoading] = useState(false)

  const fetchLogs = async (newOffset = 0, append = false) => {
    setTableLoading(true)
    try {
      const data = await getPointsLogs({ limit: PAGE_SIZE, offset: newOffset })
      if (append) {
        setLogs(prev => [...prev, ...data])
      } else {
        setLogs(data)
      }
      setHasMore(data.length === PAGE_SIZE)
      setOffset(newOffset)
    } catch {
      message.error('获取调用记录失败')
    } finally {
      setTableLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs(0).finally(() => setLoading(false))
  }, [])

  // 从积分日志推算统计数据
  const callLogs = logs.filter(l => l.type === 1)
  const totalConsumed = callLogs.reduce((sum, l) => sum + Math.abs(l.amount), 0)
  const totalEarned = logs
    .filter(l => l.type === 2)
    .reduce((sum, l) => sum + l.amount, 0)

  // 模型使用统计
  const modelStats: Record<string, number> = {}
  callLogs.forEach(l => {
    if (l.model) {
      modelStats[l.model] = (modelStats[l.model] || 0) + 1
    }
  })
  const topModel = Object.entries(modelStats).sort((a, b) => b[1] - a[1])[0]

  const columns: ColumnsType<PointsLog> = [
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 110,
      render: (type: number) => {
        const colorMap: Record<number, string> = { 1: 'red', 2: 'green', 3: 'blue', 4: 'purple' }
        return <Tag color={colorMap[type] || 'default'}>{getPointsTypeLabel(type)}</Tag>
      },
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model || '-',
    },
    {
      title: '积分变动',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      render: (amount: number) => (
        <span style={{ color: amount > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
          {amount > 0 ? '+' : ''}{amount}
        </span>
      ),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      render: (remark: string | null) => remark || '-',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts: string) => formatTimestamp(ts),
    },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="总调用次数"
              value={callLogs.length}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="总消耗积分"
              value={totalConsumed}
              suffix="分"
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: 8 }}>
            <Statistic
              title="托管收益积分"
              value={totalEarned}
              suffix="分"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {topModel && (
        <Card style={{ marginBottom: 16, borderRadius: 8 }}>
          <Statistic
            title="最常用模型"
            value={topModel[0]}
            suffix={`（${topModel[1]} 次）`}
          />
        </Card>
      )}

      <Card
        title={<Title level={5} style={{ margin: 0 }}>调用记录</Title>}
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => fetchLogs(0)}>
            刷新
          </Button>
        }
        style={{ borderRadius: 8 }}
      >
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={tableLoading}
          pagination={false}
          scroll={{ x: 600 }}
          size="middle"
        />
        {hasMore && (
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Button onClick={() => fetchLogs(offset + PAGE_SIZE, true)} loading={tableLoading}>
              加载更多
            </Button>
          </div>
        )}
        {!hasMore && logs.length > 0 && (
          <div style={{ textAlign: 'center', marginTop: 16, color: '#999' }}>
            已加载全部记录（共 {logs.length} 条）
          </div>
        )}
      </Card>
    </div>
  )
}

export default StatsPage

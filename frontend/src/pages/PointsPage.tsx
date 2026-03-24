import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Typography,
  Statistic,
  Spin,
  message,
  Button,
} from 'antd'
import { WalletOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { getBalance, getPointsLogs } from '../api/points'
import type { PointsLog } from '../types'
import { formatTimestamp, getPointsTypeLabel } from '../utils'

const { Title } = Typography

const PAGE_SIZE = 20

const typeColorMap: Record<number, string> = {
  1: 'red',
  2: 'green',
  3: 'blue',
  4: 'purple',
}

const PointsPage: React.FC = () => {
  const [balance, setBalance] = useState<number>(0)
  const [logs, setLogs] = useState<PointsLog[]>([])
  const [loading, setLoading] = useState(true)
  const [tableLoading, setTableLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)

  const fetchBalance = async () => {
    try {
      const data = await getBalance()
      setBalance(data.balance)
    } catch {
      message.error('获取积分余额失败')
    }
  }

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
      message.error('获取积分明细失败')
    } finally {
      setTableLoading(false)
    }
  }

  useEffect(() => {
    Promise.all([fetchBalance(), fetchLogs(0)]).finally(() => setLoading(false))
  }, [])

  const handleRefresh = () => {
    fetchBalance()
    fetchLogs(0)
  }

  const handleLoadMore = () => {
    fetchLogs(offset + PAGE_SIZE, true)
  }

  const columns: ColumnsType<PointsLog> = [
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: number) => (
        <Tag color={typeColorMap[type] || 'default'}>{getPointsTypeLabel(type)}</Tag>
      ),
    },
    {
      title: '变动量',
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
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model || '-',
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
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card style={{ marginBottom: 16, borderRadius: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Statistic
            title="当前积分余额"
            value={balance}
            prefix={<WalletOutlined />}
            suffix="分"
            valueStyle={{ color: '#1677ff', fontSize: 32 }}
          />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
        </div>
      </Card>

      <Card
        title={<Title level={5} style={{ margin: 0 }}>积分明细</Title>}
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
            <Button onClick={handleLoadMore} loading={tableLoading}>
              加载更多
            </Button>
          </div>
        )}
        {!hasMore && logs.length > 0 && (
          <div style={{ textAlign: 'center', marginTop: 16, color: '#999' }}>
            已加载全部记录（共 {logs.length} 条）
          </div>
        )}
        {logs.length === 0 && !tableLoading && (
          <div style={{ textAlign: 'center', marginTop: 16, color: '#999' }}>
            暂无积分记录
          </div>
        )}
      </Card>
    </div>
  )
}

export default PointsPage

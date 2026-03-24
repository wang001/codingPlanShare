import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Typography,
  Spin,
  message,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { adminGetLogs } from '../../api/admin'
import type { AdminLog } from '../../types'
import { formatTimestamp, getPointsTypeLabel } from '../../utils'

const { Title } = Typography

const PAGE_SIZE = 50

const typeColorMap: Record<number, string> = {
  1: 'red',
  2: 'green',
  3: 'blue',
  4: 'purple',
}

const AdminLogs: React.FC = () => {
  const [logs, setLogs] = useState<AdminLog[]>([])
  const [loading, setLoading] = useState(true)
  const [tableLoading, setTableLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)

  const fetchLogs = async (newOffset = 0, append = false) => {
    setTableLoading(true)
    try {
      const data = await adminGetLogs({ limit: PAGE_SIZE, offset: newOffset })
      if (append) {
        setLogs(prev => [...prev, ...data])
      } else {
        setLogs(data)
      }
      setHasMore(data.length === PAGE_SIZE)
      setOffset(newOffset)
    } catch {
      message.error('获取日志失败')
    } finally {
      setTableLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs(0).finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<AdminLog> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
    },
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 80,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 110,
      render: (type: number) => (
        <Tag color={typeColorMap[type] || 'default'}>{getPointsTypeLabel(type)}</Tag>
      ),
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
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model || '-',
    },
    {
      title: '关联密钥ID',
      dataIndex: 'related_key_id',
      key: 'related_key_id',
      width: 110,
      render: (id: number | null) => id ?? '-',
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
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <Card
        title={<Title level={5} style={{ margin: 0 }}>调用日志</Title>}
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
          scroll={{ x: 750 }}
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
            已加载全部日志（共 {logs.length} 条）
          </div>
        )}
      </Card>
    </div>
  )
}

export default AdminLogs

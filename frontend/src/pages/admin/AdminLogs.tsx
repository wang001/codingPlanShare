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
import { formatTimestamp } from '../../utils'

const { Title } = Typography

const PAGE_SIZE = 50

const statusColorMap: Record<number, string> = {
  0: 'red',
  1: 'green',
}
const statusLabelMap: Record<number, string> = {
  0: '失败',
  1: '成功',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: number) => (
        <Tag color={statusColorMap[status] ?? 'default'}>{statusLabelMap[status] ?? '未知'}</Tag>
      ),
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model || '-',
    },
    {
      title: '厂商密钥ID',
      dataIndex: 'provider_key_id',
      key: 'provider_key_id',
      width: 110,
      render: (id: number | null) => id ?? '-',
    },
    {
      title: '错误信息',
      dataIndex: 'error_msg',
      key: 'error_msg',
      render: (msg: string | null) => msg
        ? <span style={{ color: '#ff4d4f', fontSize: 12 }}>{msg.slice(0, 50)}{msg.length > 50 ? '…' : ''}</span>
        : '-',
    },
    {
      title: 'IP',
      dataIndex: 'ip',
      key: 'ip',
      width: 120,
      render: (ip: string | null) => ip || '-',
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

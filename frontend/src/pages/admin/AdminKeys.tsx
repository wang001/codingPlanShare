import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Select,
  Space,
  Popconfirm,
  Spin,
  message,
  Typography,
  Tooltip,
} from 'antd'
import {
  DeleteOutlined,
  ReloadOutlined,
  CopyOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { adminGetKeys, adminUpdateKeyStatus, adminDeleteKey } from '../../api/admin'
import type { Key } from '../../types'
import {
  formatTimestamp,
  getKeyStatusLabel,
  getKeyStatusColor,
  getKeyTypeLabel,
  getProviderLabel,
} from '../../utils'

const { Title } = Typography

const statusOptions = [
  { label: '正常', value: 0 },
  { label: '禁用', value: 2 },
  { label: '超限', value: 3 },
  { label: '无效', value: 4 },
]

const AdminKeys: React.FC = () => {
  const [keys, setKeys] = useState<Key[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  const fetchKeys = async () => {
    setLoading(true)
    try {
      const data = await adminGetKeys()
      setKeys(data.filter(k => k.status !== 1)) // 过滤已删除
    } catch {
      message.error('获取密钥列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchKeys() }, [])

  const handleStatusChange = async (id: number, status: 0 | 1 | 2 | 3 | 4) => {
    setActionLoading(id)
    try {
      await adminUpdateKeyStatus(id, status)
      message.success('状态更新成功')
      fetchKeys()
    } catch {
      message.error('状态更新失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: number) => {
    setActionLoading(id)
    try {
      await adminDeleteKey(id)
      message.success('删除成功')
      fetchKeys()
    } catch {
      message.error('删除失败')
    } finally {
      setActionLoading(null)
    }
  }

  const columns: ColumnsType<Key> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'key_type',
      key: 'key_type',
      width: 120,
      render: (type: number) => (
        <Tag color={type === 1 ? 'blue' : 'green'}>{getKeyTypeLabel(type)}</Tag>
      ),
    },
    {
      title: '厂商',
      dataIndex: 'provider',
      key: 'provider',
      width: 90,
      render: (provider: string | null) => getProviderLabel(provider),
    },
    {
      title: '密钥值',
      dataIndex: 'encrypted_key',
      key: 'encrypted_key',
      width: 200,
      render: (key: string) => {
        if (!key) return '-'
        const masked = key.length > 12
          ? `${key.slice(0, 6)}...${key.slice(-4)}`
          : key
        return (
          <Tooltip title={key}>
            <Space size={4}>
              <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{masked}</span>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => {
                  navigator.clipboard.writeText(key)
                  message.success('已复制')
                }}
              />
            </Space>
          </Tooltip>
        )
      },
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
      width: 90,
      render: (status: number) => (
        <Tag color={getKeyStatusColor(status)}>{getKeyStatusLabel(status)}</Tag>
      ),
    },
    {
      title: '使用次数',
      dataIndex: 'used_count',
      key: 'used_count',
      width: 90,
    },
    {
      title: '最后使用',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 175,
      render: (ts: string | null) => formatTimestamp(ts),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 175,
      render: (ts: string) => formatTimestamp(ts),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: Key) => (
        <Space>
          <Select
            size="small"
            value={record.status}
            style={{ width: 90 }}
            options={statusOptions}
            loading={actionLoading === record.id}
            onChange={(val) => handleStatusChange(record.id, val as 0 | 1 | 2 | 3 | 4)}
          />
          <Popconfirm
            title="确认删除此密钥？"
            okText="确认"
            cancelText="取消"
            onConfirm={() => handleDelete(record.id)}
          >
            <Tooltip title="删除">
              <Button
                size="small"
                type="text"
                danger
                icon={<DeleteOutlined />}
                loading={actionLoading === record.id}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
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
        title={<Title level={5} style={{ margin: 0 }}>密钥管理</Title>}
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchKeys}>刷新</Button>
        }
        style={{ borderRadius: 8 }}
      >
        <Table
          columns={columns}
          dataSource={keys}
          rowKey="id"
          scroll={{ x: 900 }}
          size="middle"
          pagination={{ pageSize: 15 }}
        />
      </Card>
    </div>
  )
}

export default AdminKeys

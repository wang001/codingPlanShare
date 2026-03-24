import React, { useEffect, useState } from 'react'
import {
  Table,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Popconfirm,
  Spin,
  message,
  Tabs,
  Tooltip,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  StopOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { getKeys, createKey, updateKey, deleteKey } from '../api/keys'
import type { Key, KeyProvider } from '../types'
import {
  formatTimestamp,
  getKeyStatusLabel,
  getKeyStatusColor,
  getProviderLabel,
} from '../utils'

const providerOptions: { label: string; value: KeyProvider }[] = [
  { label: '智谱', value: 'zhipu' },
  { label: 'MiniMax', value: 'minimax' },
  { label: '阿里云', value: 'alibaba' },
  { label: '腾讯云', value: 'tencent' },
  { label: '百度', value: 'baidu' },
]

const KeysPage: React.FC = () => {
  const [keys, setKeys] = useState<Key[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // 创建密钥弹窗
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createType, setCreateType] = useState<1 | 2>(1)
  const [createLoading, setCreateLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchKeys = async () => {
    setLoading(true)
    try {
      const data = await getKeys()
      setKeys(data)
    } catch {
      message.error('获取密钥列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchKeys() }, [])

  // 平台密钥和厂商密钥分开
  const platformKeys = keys.filter(k => k.key_type === 1 && k.status !== 1)
  const vendorKeys = keys.filter(k => k.key_type === 2 && k.status !== 1)

  const handleCreateKey = async (values: any) => {
    setCreateLoading(true)
    try {
      await createKey({
        name: values.name,
        key_type: createType,
        provider: createType === 2 ? values.provider : undefined,
        encrypted_key: createType === 2 ? values.encrypted_key : undefined,
      })
      message.success('创建密钥成功')
      setCreateModalOpen(false)
      form.resetFields()
      fetchKeys()
    } catch {
      message.error('创建密钥失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleToggleStatus = async (key: Key) => {
    const newStatus = key.status === 0 ? 2 : 0
    setActionLoading(key.id)
    try {
      await updateKey(key.id, { status: newStatus })
      message.success(newStatus === 0 ? '已启用' : '已禁用')
      fetchKeys()
    } catch {
      message.error('操作失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: number) => {
    setActionLoading(id)
    try {
      await deleteKey(id)
      message.success('删除成功')
      fetchKeys()
    } catch {
      message.error('删除失败')
    } finally {
      setActionLoading(null)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      message.success('已复制到剪贴板')
    }).catch(() => {
      message.error('复制失败')
    })
  }

  const platformColumns: ColumnsType<Key> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '密钥（隐藏）',
      dataIndex: 'encrypted_key',
      key: 'encrypted_key',
      render: (key: string | undefined, record: Key) => {
        const displayKey = key ? `${key.slice(0, 8)}...${key.slice(-4)}` : `ID: ${record.id}`
        return (
          <Space>
            <span style={{ fontFamily: 'monospace' }}>{displayKey}</span>
            {key && (
              <Tooltip title="复制完整密钥">
                <Button
                  size="small"
                  type="text"
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard(key)}
                />
              </Tooltip>
            )}
          </Space>
        )
      },
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
      width: 180,
      render: (ts: string | null) => formatTimestamp(ts),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts: string) => formatTimestamp(ts),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: Key) => (
        <Space>
          <Tooltip title={record.status === 0 ? '禁用' : '启用'}>
            <Button
              size="small"
              type="text"
              icon={record.status === 0 ? <StopOutlined /> : <CheckCircleOutlined />}
              loading={actionLoading === record.id}
              onClick={() => handleToggleStatus(record)}
            />
          </Tooltip>
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

  const vendorColumns: ColumnsType<Key> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '厂商',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (provider: string | null) => getProviderLabel(provider),
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
      width: 180,
      render: (ts: string | null) => formatTimestamp(ts),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts: string) => formatTimestamp(ts),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: Key) => (
        <Space>
          <Tooltip title={record.status === 0 ? '禁用' : '启用'}>
            <Button
              size="small"
              type="text"
              icon={record.status === 0 ? <StopOutlined /> : <CheckCircleOutlined />}
              loading={actionLoading === record.id}
              onClick={() => handleToggleStatus(record)}
            />
          </Tooltip>
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
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Tabs
        defaultActiveKey="platform"
        tabBarExtraContent={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchKeys}>刷新</Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setCreateType(1)
                form.resetFields()
                setCreateModalOpen(true)
              }}
            >
              新建平台密钥
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                setCreateType(2)
                form.resetFields()
                setCreateModalOpen(true)
              }}
            >
              托管厂商密钥
            </Button>
          </Space>
        }
        items={[
          {
            key: 'platform',
            label: `平台密钥（${platformKeys.length}）`,
            children: (
              <Table
                columns={platformColumns}
                dataSource={platformKeys}
                rowKey="id"
                scroll={{ x: 700 }}
                size="middle"
                pagination={{ pageSize: 10 }}
              />
            ),
          },
          {
            key: 'vendor',
            label: `厂商密钥（${vendorKeys.length}）`,
            children: (
              <Table
                columns={vendorColumns}
                dataSource={vendorKeys}
                rowKey="id"
                scroll={{ x: 700 }}
                size="middle"
                pagination={{ pageSize: 10 }}
              />
            ),
          },
        ]}
      />

      <Modal
        title={createType === 1 ? '新建平台密钥' : '托管厂商密钥'}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateKey}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="name"
            label="密钥名称"
            rules={[{ required: true, message: '请输入密钥名称' }]}
          >
            <Input placeholder="例如：生产环境密钥" />
          </Form.Item>

          {createType === 2 && (
            <>
              <Form.Item
                name="provider"
                label="厂商"
                rules={[{ required: true, message: '请选择厂商' }]}
              >
                <Select
                  placeholder="请选择厂商"
                  options={providerOptions}
                />
              </Form.Item>
              <Form.Item
                name="encrypted_key"
                label="厂商 API 密钥"
                rules={[{ required: true, message: '请输入厂商 API 密钥' }]}
              >
                <Input.Password placeholder="请输入原始 API 密钥" />
              </Form.Item>
            </>
          )}

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCreateModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={createLoading}>
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default KeysPage

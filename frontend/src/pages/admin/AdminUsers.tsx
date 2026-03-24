import React, { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Space,
  Spin,
  message,
  Typography,
} from 'antd'
import {
  PlusOutlined,
  StopOutlined,
  CheckCircleOutlined,
  WalletOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  adminGetUsers,
  adminCreateUser,
  adminUpdateUserStatus,
  adminAdjustPoints,
} from '../../api/admin'
import type { User } from '../../types'
import { formatTimestamp, getUserStatusLabel } from '../../utils'

const { Title } = Typography

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // 创建用户弹窗
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [createForm] = Form.useForm()

  // 调整积分弹窗
  const [pointsModalOpen, setPointsModalOpen] = useState(false)
  const [pointsUser, setPointsUser] = useState<User | null>(null)
  const [pointsLoading, setPointsLoading] = useState(false)
  const [pointsForm] = Form.useForm()

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const data = await adminGetUsers()
      setUsers(data)
    } catch {
      message.error('获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  const handleCreateUser = async (values: { username: string; email: string; password: string }) => {
    setCreateLoading(true)
    try {
      await adminCreateUser(values)
      message.success('创建用户成功')
      setCreateModalOpen(false)
      createForm.resetFields()
      fetchUsers()
    } catch {
      message.error('创建用户失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleToggleStatus = async (user: User) => {
    const newStatus: 0 | 1 = user.status === 0 ? 1 : 0
    setActionLoading(user.id)
    try {
      await adminUpdateUserStatus(user.id, newStatus)
      message.success(newStatus === 0 ? '已启用用户' : '已禁用用户')
      fetchUsers()
    } catch {
      message.error('操作失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleAdjustPoints = async (values: { amount: number; remark: string }) => {
    if (!pointsUser) return
    setPointsLoading(true)
    try {
      await adminAdjustPoints({
        user_id: pointsUser.id,
        amount: values.amount,
        remark: values.remark,
      })
      message.success('积分调整成功')
      setPointsModalOpen(false)
      pointsForm.resetFields()
      fetchUsers()
    } catch {
      message.error('积分调整失败')
    } finally {
      setPointsLoading(false)
    }
  }

  const openPointsModal = (user: User) => {
    setPointsUser(user)
    pointsForm.resetFields()
    setPointsModalOpen(true)
  }

  const columns: ColumnsType<User> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '积分余额',
      dataIndex: 'balance',
      key: 'balance',
      width: 100,
      render: (balance: number) => (
        <span style={{ fontWeight: 600, color: '#1677ff' }}>{balance}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: number) => (
        <Tag color={status === 0 ? 'success' : 'error'}>{getUserStatusLabel(status)}</Tag>
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts: string) => formatTimestamp(ts),
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, record: User) => (
        <Space>
          <Button
            size="small"
            icon={<WalletOutlined />}
            onClick={() => openPointsModal(record)}
          >
            积分
          </Button>
          <Button
            size="small"
            type={record.status === 0 ? 'default' : 'primary'}
            danger={record.status === 0}
            icon={record.status === 0 ? <StopOutlined /> : <CheckCircleOutlined />}
            loading={actionLoading === record.id}
            onClick={() => handleToggleStatus(record)}
          >
            {record.status === 0 ? '禁用' : '启用'}
          </Button>
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
      <Card
        title={<Title level={5} style={{ margin: 0 }}>用户管理</Title>}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchUsers}>刷新</Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                createForm.resetFields()
                setCreateModalOpen(true)
              }}
            >
              创建用户
            </Button>
          </Space>
        }
        style={{ borderRadius: 8 }}
      >
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          scroll={{ x: 700 }}
          size="middle"
          pagination={{ pageSize: 15 }}
        />
      </Card>

      {/* 创建用户弹窗 */}
      <Modal
        title="创建用户"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateUser}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效邮箱' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入初始密码" />
          </Form.Item>
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

      {/* 积分调整弹窗 */}
      <Modal
        title={`调整积分 - ${pointsUser?.username}`}
        open={pointsModalOpen}
        onCancel={() => setPointsModalOpen(false)}
        footer={null}
        destroyOnClose
      >
        <div style={{ marginBottom: 12, color: '#666' }}>
          当前余额：<strong>{pointsUser?.balance ?? 0}</strong> 分
        </div>
        <Form
          form={pointsForm}
          layout="vertical"
          onFinish={handleAdjustPoints}
        >
          <Form.Item
            name="amount"
            label="调整数量（正数增加，负数减少）"
            rules={[{ required: true, message: '请输入调整数量' }]}
          >
            <InputNumber style={{ width: '100%' }} placeholder="例如：100 或 -50" />
          </Form.Item>
          <Form.Item
            name="remark"
            label="备注"
            rules={[{ required: true, message: '请输入备注' }]}
          >
            <Input placeholder="请输入调整原因" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setPointsModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={pointsLoading}>
                确认调整
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AdminUsers

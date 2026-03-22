import React, { useState, useEffect } from 'react'

interface KeysPageProps {
  user: any
}

const KeysPage: React.FC<KeysPageProps> = () => {
  const [platformKeys, setPlatformKeys] = useState<any[]>([])
  const [vendorKeys, setVendorKeys] = useState<any[]>([])
  const [showAddKey, setShowAddKey] = useState(false)
  const [newKey, setNewKey] = useState({
    name: '',
    provider: '',
    key: ''
  })

  useEffect(() => {
    // 模拟获取密钥列表
    const mockPlatformKeys = [
      { id: 1, key: 'sk-xxxxxxxxxxxxxxxxxxxxxxxx', status: '正常', created_at: '2026-03-20 10:00:00' },
      { id: 2, key: 'sk-yyyyyyyyyyyyyyyyyyyyyyyy', status: '禁用', created_at: '2026-03-19 15:30:00' },
    ]
    const mockVendorKeys = [
      { id: 1, name: 'ZhipuAI', provider: 'zhipu', status: '正常', created_at: '2026-03-18 09:15:00' },
      { id: 2, name: 'OpenAI', provider: 'openai', status: '正常', created_at: '2026-03-17 14:00:00' },
    ]
    setPlatformKeys(mockPlatformKeys)
    setVendorKeys(mockVendorKeys)
  }, [])

  const handleAddKey = () => {
    // 模拟添加密钥
    const newVendorKey = {
      id: vendorKeys.length + 1,
      name: newKey.name,
      provider: newKey.provider,
      status: '正常',
      created_at: new Date().toLocaleString()
    }
    setVendorKeys([...vendorKeys, newVendorKey])
    setNewKey({ name: '', provider: '', key: '' })
    setShowAddKey(false)
  }

  return (
    <div className="container">
      <div className="card mb-20">
        <h2>密钥管理</h2>
      </div>

      <div className="card mb-20">
        <div className="row">
          <div className="col">
            <h3>平台密钥</h3>
          </div>
          <div className="col" style={{ textAlign: 'right' }}>
            <button className="btn btn-primary">生成新密钥</button>
          </div>
        </div>
        <div style={{ overflowX: 'auto', marginTop: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e8e8e8' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>密钥</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>状态</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>创建时间</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {platformKeys.map((key) => (
                <tr key={key.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px' }}>{key.key}</td>
                  <td style={{ padding: '12px', color: key.status === '正常' ? 'green' : 'red' }}>
                    {key.status}
                  </td>
                  <td style={{ padding: '12px' }}>{key.created_at}</td>
                  <td style={{ padding: '12px' }}>
                    <button className="btn btn-secondary" style={{ marginRight: '10px' }}>
                      {key.status === '正常' ? '禁用' : '启用'}
                    </button>
                    <button className="btn btn-secondary">删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="row">
          <div className="col">
            <h3>厂商密钥</h3>
          </div>
          <div className="col" style={{ textAlign: 'right' }}>
            <button className="btn btn-primary" onClick={() => setShowAddKey(true)}>
              添加密钥
            </button>
          </div>
        </div>
        
        {showAddKey && (
          <div className="card" style={{ marginTop: '20px' }}>
            <h4>添加厂商密钥</h4>
            <div className="row">
              <div className="col">
                <label>密钥名称</label>
                <input
                  type="text"
                  value={newKey.name}
                  onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                  placeholder="请输入密钥名称"
                />
              </div>
              <div className="col">
                <label>厂商</label>
                <select
                  value={newKey.provider}
                  onChange={(e) => setNewKey({ ...newKey, provider: e.target.value })}
                >
                  <option value="">请选择厂商</option>
                  <option value="zhipu">ZhipuAI</option>
                  <option value="openai">OpenAI</option>
                  <option value="minimax">Minimax</option>
                  <option value="alibaba">Alibaba</option>
                  <option value="tencent">Tencent</option>
                  <option value="baidu">Baidu</option>
                </select>
              </div>
            </div>
            <div>
              <label>API密钥</label>
              <input
                type="text"
                value={newKey.key}
                onChange={(e) => setNewKey({ ...newKey, key: e.target.value })}
                placeholder="请输入API密钥"
              />
            </div>
            <div style={{ marginTop: '10px', textAlign: 'right' }}>
              <button className="btn btn-secondary" onClick={() => setShowAddKey(false)} style={{ marginRight: '10px' }}>
                取消
              </button>
              <button className="btn btn-primary" onClick={handleAddKey}>
                保存
              </button>
            </div>
          </div>
        )}

        <div style={{ overflowX: 'auto', marginTop: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e8e8e8' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>名称</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>厂商</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>状态</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>创建时间</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {vendorKeys.map((key) => (
                <tr key={key.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px' }}>{key.name}</td>
                  <td style={{ padding: '12px' }}>{key.provider}</td>
                  <td style={{ padding: '12px', color: key.status === '正常' ? 'green' : 'red' }}>
                    {key.status}
                  </td>
                  <td style={{ padding: '12px' }}>{key.created_at}</td>
                  <td style={{ padding: '12px' }}>
                    <button className="btn btn-secondary" style={{ marginRight: '10px' }}>
                      {key.status === '正常' ? '禁用' : '启用'}
                    </button>
                    <button className="btn btn-secondary">删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default KeysPage
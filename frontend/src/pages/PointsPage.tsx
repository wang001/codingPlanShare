import React, { useState, useEffect } from 'react'

interface PointsPageProps {
  user: any
}

const PointsPage: React.FC<PointsPageProps> = ({ user }) => {
  const [points] = useState(user.balance)
  const [pointLogs, setPointLogs] = useState<any[]>([])

  useEffect(() => {
    // 模拟获取积分明细
    const mockLogs = [
      { id: 1, amount: -10, type: '调用消耗', model: 'GLM-5', created_at: '2026-03-20 10:00:00' },
      { id: 2, amount: 50, type: '托管收益', model: 'GPT-4', created_at: '2026-03-19 15:30:00' },
      { id: 3, amount: -5, type: '调用消耗', model: 'GLM-5', created_at: '2026-03-18 09:15:00' },
      { id: 4, amount: 100, type: '管理员调整', model: '', created_at: '2026-03-17 14:00:00' },
    ]
    setPointLogs(mockLogs)
  }, [])

  return (
    <div className="container">
      <div className="card mb-20">
        <h2>积分管理</h2>
        <div style={{ fontSize: '24px', fontWeight: 'bold', margin: '20px 0' }}>
          当前余额: {points} 积分
        </div>
      </div>

      <div className="card">
        <h3>积分明细</h3>
        <div style={{ overflowX: 'auto', marginTop: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e8e8e8' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>类型</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>数量</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>模型</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>时间</th>
              </tr>
            </thead>
            <tbody>
              {pointLogs.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px' }}>{log.type}</td>
                  <td style={{ padding: '12px', color: log.amount > 0 ? 'green' : 'red' }}>
                    {log.amount > 0 ? '+' : ''}{log.amount}
                  </td>
                  <td style={{ padding: '12px' }}>{log.model || '-'}</td>
                  <td style={{ padding: '12px' }}>{log.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default PointsPage
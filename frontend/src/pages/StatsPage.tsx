import React, { useState, useEffect } from 'react'

interface StatsPageProps {
  user: any
}

const StatsPage: React.FC<StatsPageProps> = () => {
  const [stats, setStats] = useState({
    totalCalls: 0,
    successRate: 0,
    popularModel: '',
    monthlyCalls: [] as { month: string; calls: number }[]
  })

  useEffect(() => {
    // 模拟获取统计数据
    const mockStats = {
      totalCalls: 1234,
      successRate: 98.5,
      popularModel: 'GLM-5',
      monthlyCalls: [
        { month: '1月', calls: 120 },
        { month: '2月', calls: 180 },
        { month: '3月', calls: 250 },
        { month: '4月', calls: 320 },
        { month: '5月', calls: 364 }
      ]
    }
    setStats(mockStats)
  }, [])

  return (
    <div className="container">
      <div className="card mb-20">
        <h2>调用统计</h2>
      </div>

      <div className="row">
        <div className="col">
          <div className="card">
            <h3>总调用次数</h3>
            <div style={{ fontSize: '36px', fontWeight: 'bold', margin: '20px 0' }}>
              {stats.totalCalls}
            </div>
          </div>
        </div>
        <div className="col">
          <div className="card">
            <h3>成功率</h3>
            <div style={{ fontSize: '36px', fontWeight: 'bold', margin: '20px 0', color: 'green' }}>
              {stats.successRate}%
            </div>
          </div>
        </div>
        <div className="col">
          <div className="card">
            <h3>最常用模型</h3>
            <div style={{ fontSize: '24px', fontWeight: 'bold', margin: '20px 0' }}>
              {stats.popularModel}
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-20">
        <h3>月度调用趋势</h3>
        <div style={{ marginTop: '20px' }}>
          <div style={{ height: '300px', border: '1px solid #e8e8e8', borderRadius: '4px', padding: '20px' }}>
            {/* 这里可以使用ECharts等库绘制图表，现在使用简单的柱状图模拟 */}
            <div style={{ display: 'flex', alignItems: 'flex-end', height: '250px', gap: '20px' }}>
              {stats.monthlyCalls.map((item, index) => {
                const maxCalls = Math.max(...stats.monthlyCalls.map(m => m.calls));
                const height = (item.calls / maxCalls) * 200;
                return (
                  <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div 
                      style={{
                        width: '100%', 
                        backgroundColor: '#1890ff',
                        borderTopLeftRadius: '4px',
                        borderTopRightRadius: '4px',
                        height: height + 'px'
                      }}
                    />
                    <div style={{ marginTop: '10px', fontSize: '12px' }}>{item.month}</div>
                    <div style={{ fontSize: '12px' }}>{item.calls}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-20">
        <h3>最近调用记录</h3>
        <div style={{ overflowX: 'auto', marginTop: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e8e8e8' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>时间</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>模型</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>状态</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>耗时</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>消耗积分</th>
              </tr>
            </thead>
            <tbody>
              {[1, 2, 3, 4, 5].map((i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px' }}>{new Date(Date.now() - i * 3600000).toLocaleString()}</td>
                  <td style={{ padding: '12px' }}>GLM-5</td>
                  <td style={{ padding: '12px', color: 'green' }}>成功</td>
                  <td style={{ padding: '12px' }}>{(Math.random() * 2 + 0.5).toFixed(2)}s</td>
                  <td style={{ padding: '12px' }}>10</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default StatsPage
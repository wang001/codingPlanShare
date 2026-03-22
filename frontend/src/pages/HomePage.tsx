import React from 'react'
import { Link } from 'react-router-dom'

interface HomePageProps {
  user: any
  onLogout: () => void
}

const HomePage: React.FC<HomePageProps> = ({ user, onLogout }) => {
  return (
    <div className="container">
      <div className="card mb-20">
        <div className="row">
          <div className="col">
            <h1>欢迎回来，{user.username}</h1>
          </div>
          <div className="col" style={{ textAlign: 'right' }}>
            <button className="btn btn-secondary" onClick={onLogout}>
              退出登录
            </button>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col">
          <div className="card">
            <h3>积分余额</h3>
            <div style={{ fontSize: '24px', fontWeight: 'bold', margin: '20px 0' }}>
              {user.balance} 积分
            </div>
            <Link to="/points">
              <button className="btn btn-primary">查看积分明细</button>
            </Link>
          </div>
        </div>
        <div className="col">
          <div className="card">
            <h3>快捷操作</h3>
            <div style={{ margin: '20px 0' }}>
              <Link to="/keys">
                <button className="btn btn-primary" style={{ width: '100%', marginBottom: '10px' }}>
                  管理API密钥
                </button>
              </Link>
              <Link to="/stats">
                <button className="btn btn-primary" style={{ width: '100%' }}>
                  查看调用统计
                </button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-20">
        <h3>使用说明</h3>
        <ul style={{ margin: '20px 0', paddingLeft: '20px' }}>
          <li>通过API密钥调用LLM模型</li>
          <li>每次调用会扣除相应积分</li>
          <li>可以托管厂商密钥获取积分收益</li>
          <li>在密钥管理页面查看和管理密钥</li>
          <li>在积分页面查看积分明细</li>
        </ul>
      </div>
    </div>
  )
}

export default HomePage
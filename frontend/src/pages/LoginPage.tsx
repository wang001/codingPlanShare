import React, { useState } from 'react'

interface LoginPageProps {
  onLogin: (userData: any) => void
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (username && password) {
      try {
        // 调用后端API进行登录验证
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email: username, password })
        })
        
        if (response.ok) {
          const userData = await response.json()
          onLogin(userData)
        } else {
          const errorData = await response.json()
          setError(errorData.detail || '登录失败')
        }
      } catch (error) {
        console.error('登录请求失败:', error)
        setError('网络错误，请稍后重试')
      }
    } else {
      setError('请输入用户名和密码')
    }
  }

  return (
    <div className="container" style={{ maxWidth: '400px', margin: '100px auto' }}>
      <div className="card">
        <h2 className="text-center mb-20">登录</h2>
        {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}
        <form onSubmit={handleSubmit} autoComplete="off">
          <div className="mb-20">
            <label htmlFor="username">用户名</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
            />
          </div>
          <div className="mb-20">
            <label htmlFor="password">密码</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
            登录
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
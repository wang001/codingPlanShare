import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import PointsPage from './pages/PointsPage'
import KeysPage from './pages/KeysPage'
import StatsPage from './pages/StatsPage'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<any>(null)

  const handleLogin = (userData: any) => {
    setUser(userData)
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    setUser(null)
    setIsAuthenticated(false)
  }

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="/" element={isAuthenticated ? <HomePage user={user} onLogout={handleLogout} /> : <Navigate to="/login" />} />
        <Route path="/points" element={isAuthenticated ? <PointsPage user={user} /> : <Navigate to="/login" />} />
        <Route path="/keys" element={isAuthenticated ? <KeysPage user={user} /> : <Navigate to="/login" />} />
        <Route path="/stats" element={isAuthenticated ? <StatsPage user={user} /> : <Navigate to="/login" />} />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/login"} />} />
      </Routes>
    </Router>
  )
}

export default App
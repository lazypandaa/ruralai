import React, { useState, useEffect } from 'react'
import { User, Mail, Lock, MapPin, Globe, Loader } from 'lucide-react'
import axios from 'axios'

function Auth({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    language: 'en',
    location: ''
  })
  const [isDetectingLocation, setIsDetectingLocation] = useState(false)

  const detectLocation = async () => {
    setIsDetectingLocation(true)
    try {
      const response = await axios.get('http://localhost:8000/api/location')
      if (response.data.location) {
        setFormData(prev => ({ ...prev, location: response.data.location }))
      }
    } catch (err) {
      console.error('Location detection failed:', err)
    } finally {
      setIsDetectingLocation(false)
    }
  }

  useEffect(() => {
    if (!isLogin) {
      detectLocation()
    }
  }, [isLogin])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const endpoint = isLogin ? '/api/login' : '/api/signup'
      const payload = isLogin 
        ? { email: formData.email, password: formData.password }
        : formData

      const response = await axios.post(`http://localhost:8000${endpoint}`, payload)
      
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token)
        onLogin(response.data.access_token)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <div className="auth-logo-icon">🌾</div>
            <h2>Gram Vaani</h2>
          </div>
          <p className="auth-subtitle">
            {isLogin ? 'Welcome back to your AI assistant' : 'Join the rural revolution'}
          </p>
        </div>

        <div className="auth-toggle">
          <button 
            className={`auth-toggle-btn ${isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(true)}
          >
            Login
          </button>
          <button 
            className={`auth-toggle-btn ${!isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(false)}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <div className="input-wrapper">
              <Mail className="input-icon" size={20} />
              <input
                type="email"
                name="email"
                placeholder="Email address"
                value={formData.email}
                onChange={handleInputChange}
                required
                className="auth-input"
              />
            </div>
          </div>

          <div className="form-group">
            <div className="input-wrapper">
              <Lock className="input-icon" size={20} />
              <input
                type="password"
                name="password"
                placeholder="Password"
                value={formData.password}
                onChange={handleInputChange}
                required
                className="auth-input"
              />
            </div>
          </div>

          {!isLogin && (
            <>
              <div className="form-group">
                <div className="input-wrapper">
                  <Globe className="input-icon" size={20} />
                  <select
                    name="language"
                    value={formData.language}
                    onChange={handleInputChange}
                    className="auth-select"
                  >
                    <option value="en">🇺🇸 English</option>
                    <option value="hi">🇮🇳 Hindi</option>
                    <option value="mr">🇮🇳 Marathi</option>
                    <option value="bn">🇮🇳 Bengali</option>
                    <option value="ta">🇮🇳 Tamil</option>
                    <option value="te">🇮🇳 Telugu</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <div className="input-wrapper">
                  <MapPin className="input-icon" size={20} />
                  <input
                    type="text"
                    name="location"
                    placeholder="Location (auto-detected)"
                    value={formData.location}
                    onChange={handleInputChange}
                    required
                    className="auth-input"
                  />
                  <button
                    type="button"
                    onClick={detectLocation}
                    disabled={isDetectingLocation}
                    className="location-btn"
                  >
                    {isDetectingLocation ? <Loader className="loading" size={16} /> : '📍'}
                  </button>
                </div>
              </div>
            </>
          )}

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" disabled={isLoading} className="auth-submit">
            {isLoading ? (
              <>
                <Loader className="loading" size={20} />
                {isLogin ? 'Signing in...' : 'Creating account...'}
              </>
            ) : (
              <>
                <User size={20} />
                {isLogin ? 'Sign In' : 'Create Account'}
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button 
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="auth-link"
            >
              {isLogin ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Auth
import React, { useState, useEffect } from 'react'
import { ArrowLeft, Edit2, Save, X } from 'lucide-react'
import axios from 'axios'

function Profile({ user, onBack, onUserUpdate }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    email: user?.email || '',
    language: user?.language || 'en',
    location: user?.location || ''
  })
  const [queries, setQueries] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUserQueries()
  }, [])

  const fetchUserQueries = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/api/user-queries', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setQueries(response.data.queries || [])
    } catch (err) {
      console.error('Failed to fetch queries:', err)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      await axios.put('http://localhost:8000/api/profile', editData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      onUserUpdate(editData)
      setIsEditing(false)
    } catch (err) {
      setError('Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    setEditData({
      email: user?.email || '',
      language: user?.language || 'en',
      location: user?.location || ''
    })
    setIsEditing(false)
    setError('')
  }

  return (
    <div className="profile-container">
      <div className="profile-header">
        <button onClick={onBack} className="back-button">
          <ArrowLeft size={20} />
          Back
        </button>
        <h2>👤 My Profile</h2>
      </div>

      <div className="profile-card">
        <div className="profile-section">
          <div className="section-header">
            <h3>Profile Details</h3>
            {!isEditing ? (
              <button onClick={() => setIsEditing(true)} className="edit-button">
                <Edit2 size={16} />
                Edit
              </button>
            ) : (
              <div className="edit-actions">
                <button onClick={handleSave} disabled={loading} className="save-button">
                  <Save size={16} />
                  Save
                </button>
                <button onClick={handleCancel} className="cancel-button">
                  <X size={16} />
                  Cancel
                </button>
              </div>
            )}
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="profile-fields">
            <div className="field">
              <label>Email</label>
              {isEditing ? (
                <input
                  type="email"
                  value={editData.email}
                  onChange={(e) => setEditData({...editData, email: e.target.value})}
                />
              ) : (
                <span>{user?.email}</span>
              )}
            </div>

            <div className="field">
              <label>Language</label>
              {isEditing ? (
                <select
                  value={editData.language}
                  onChange={(e) => setEditData({...editData, language: e.target.value})}
                >
                  <option value="en">🇺🇸 English</option>
                  <option value="hi">🇮🇳 Hindi</option>
                  <option value="mr">🇮🇳 Marathi</option>
                  <option value="bn">🇮🇳 Bengali</option>
                  <option value="ta">🇮🇳 Tamil</option>
                </select>
              ) : (
                <span>
                  {editData.language === 'en' && '🇺🇸 English'}
                  {editData.language === 'hi' && '🇮🇳 Hindi'}
                  {editData.language === 'mr' && '🇮🇳 Marathi'}
                  {editData.language === 'bn' && '🇮🇳 Bengali'}
                  {editData.language === 'ta' && '🇮🇳 Tamil'}
                </span>
              )}
            </div>

            <div className="field">
              <label>Location</label>
              {isEditing ? (
                <input
                  type="text"
                  value={editData.location}
                  onChange={(e) => setEditData({...editData, location: e.target.value})}
                  placeholder="City, State"
                />
              ) : (
                <span>📍 {user?.location}</span>
              )}
            </div>
          </div>
        </div>

        <div className="queries-section">
          <h3>📋 Query History</h3>
          {queries.length === 0 ? (
            <p className="no-queries">No queries yet. Start asking questions!</p>
          ) : (
            <div className="queries-list">
              {queries.map((query, index) => (
                <div key={index} className="query-item">
                  <div className="query-header">
                    <span className="query-type">{query.type}</span>
                    <span className="query-date">{new Date(query.timestamp).toLocaleDateString()}</span>
                  </div>
                  <div className="query-text">{query.query}</div>
                  {query.response && (
                    <div className="query-response">{query.response.substring(0, 100)}...</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Profile
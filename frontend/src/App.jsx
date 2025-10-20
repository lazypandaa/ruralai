import React, { useState, useRef } from 'react'
import { Mic, MicOff, Play, Pause, Loader } from 'lucide-react'
import axios from 'axios'

function App() {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [response, setResponse] = useState('')
  const [error, setError] = useState('')
  const [audioUrl, setAudioUrl] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [inputMode, setInputMode] = useState('voice') // 'voice' or 'text'
  
  const mediaRecorderRef = useRef(null)
  const audioRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = async () => {
    try {
      setError('')
      setResponse('')
      setAudioUrl(null)
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []

      mediaRecorderRef.current.ondataavailable = (event) => {
        chunksRef.current.push(event.data)
      }

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' })
        await processAudio(audioBlob)
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (err) {
      setError('Microphone access denied. Please allow microphone access and try again.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processAudio = async (audioBlob) => {
    setIsProcessing(true)
    setError('')
    
    try {
      const formData = new FormData()
      formData.append('file', audioBlob)

      const response = await axios.post('http://localhost:8000/process-audio', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setResponse(response.data.response)
      if (response.data.audio_url) {
        const audio = new Audio(`http://localhost:8000${response.data.audio_url}`)
        await audio.play()
      }
    } catch (err) {
      setError('Failed to process audio')
      console.error(err)
    } finally {
      setIsProcessing(false)
    }
  }

  const processText = async () => {
    if (!textInput.trim()) {
      setError('Please enter some text to process.')
      return
    }

    setIsProcessing(true)
    setError('')
    setResponse('')
    setAudioUrl(null)

    try {
      const response = await axios.post('http://localhost:8000/process-text', {
        text: textInput.trim()
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      })

      setResponse(response.data)
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to process text. Please try again.'
      setError(errorMessage)
      console.error('Error processing text:', err)
    } finally {
      setIsProcessing(false)
    }
  }

  const playAudio = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        audioRef.current.play()
        setIsPlaying(true)
      }
    }
  }

  const handleAudioEnded = () => {
    setIsPlaying(false)
  }

  return (
    <div className="container">
      <div className="header">
        <h1>🌾 Gram Vaani</h1>
        <p>AI Voice Assistant for Rural India</p>
      </div>

      <div className="main-card">
        <div className="input-mode-selector">
          <button
            className={`mode-button ${inputMode === 'voice' ? 'active' : ''}`}
            onClick={() => setInputMode('voice')}
          >
            🎤 Voice
          </button>
          <button
            className={`mode-button ${inputMode === 'text' ? 'active' : ''}`}
            onClick={() => setInputMode('text')}
          >
            ✍️ Text
          </button>
        </div>

        {inputMode === 'voice' ? (
          <div className="voice-section">
            <button
              className={`voice-button ${isRecording ? 'recording' : ''}`}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <Loader className="loading" />
              ) : isRecording ? (
                <MicOff size={40} />
              ) : (
                <Mic size={40} />
              )}
            </button>
            
            <div className="status-text">
              {isRecording 
                ? "🎤 Listening... Click to stop" 
                : isProcessing 
                ? "🤖 Processing your request..." 
                : "👆 Click to speak in your local dialect"
              }
            </div>
          </div>
        ) : (
          <div className="text-section">
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your question here... (e.g., मौसम कैसा है?, crop prices, government schemes)"
              className="text-input"
              rows={3}
              disabled={isProcessing}
            />
            <button
              className="submit-button"
              onClick={processText}
              disabled={isProcessing || !textInput.trim()}
            >
              {isProcessing ? (
                <>
                  <Loader className="loading" size={16} />
                  Processing...
                </>
              ) : (
                'Submit Question'
              )}
            </button>
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {response && (
          <div className="response-section">
            <h3>📝 Transcript:</h3>
            <p className="response-text">{response.transcript}</p>
            
            <h3>💬 Response:</h3>
            <p className="response-text">{response.response_text}</p>
            
            {audioUrl && (
              <div>
                <h3>🔊 Voice Response:</h3>
                <audio
                  ref={audioRef}
                  src={audioUrl}
                  onEnded={handleAudioEnded}
                  preload="auto"
                />
                <button
                  onClick={playAudio}
                  style={{
                    background: '#667eea',
                    color: 'white',
                    border: 'none',
                    padding: '10px 20px',
                    borderRadius: '25px',
                    cursor: 'pointer',
                    marginTop: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    margin: '10px auto'
                  }}
                >
                  {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                  {isPlaying ? 'Pause' : 'Play'} Response
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="features-grid">
        <div className="feature-card">
          <div className="feature-icon">🌤️</div>
          <div className="feature-title">Weather Information</div>
          <div className="feature-description">
            Get real-time weather updates and farming advice for your location
          </div>
        </div>

        <div className="feature-card">
          <div className="feature-icon">💰</div>
          <div className="feature-title">Crop Prices</div>
          <div className="feature-description">
            Check current market prices for your crops and get selling advice
          </div>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🏛️</div>
          <div className="feature-title">Government Schemes</div>
          <div className="feature-description">
            Learn about available government schemes and how to apply
          </div>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🗣️</div>
          <div className="feature-title">Multi-Dialect Support</div>
          <div className="feature-description">
            Speak in your local language - Hindi, Telugu, Punjabi, Bhojpuri, and more
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

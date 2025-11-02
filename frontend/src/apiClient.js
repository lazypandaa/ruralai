import axios from 'axios'
import { API_URL } from './config'

// Create axios instance with retry logic
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000, // 30 second timeout
})

// Add retry interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    
    // Retry on network errors or 5xx errors
    if (
      (!error.response || error.response.status >= 500) &&
      config &&
      !config.__isRetryRequest &&
      config.retryCount < 3
    ) {
      config.__isRetryRequest = true
      config.retryCount = (config.retryCount || 0) + 1
      
      // Wait before retry (exponential backoff)
      const delay = Math.pow(2, config.retryCount) * 1000
      await new Promise(resolve => setTimeout(resolve, delay))
      
      return apiClient(config)
    }
    
    return Promise.reject(error)
  }
)

export default apiClient
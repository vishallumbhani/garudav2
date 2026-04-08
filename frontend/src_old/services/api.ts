import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://192.168.116.155:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('garuda_access_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Handle token refresh on 401
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: any) => void; reject: (e: any) => void }> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(p => error ? p.reject(error) : p.resolve(token))
  failedQueue = []
}

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => Promise.reject(err))
      }
      originalRequest._retry = true
      isRefreshing = true
      const refreshToken = localStorage.getItem('garuda_refresh_token')
      if (!refreshToken) {
        isRefreshing = false
        clearAuth()
        return Promise.reject(error)
      }
      try {
        const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
        const { access_token, refresh_token } = res.data
        localStorage.setItem('garuda_access_token', access_token)
        localStorage.setItem('garuda_refresh_token', refresh_token)
        api.defaults.headers['Authorization'] = `Bearer ${access_token}`
        processQueue(null, access_token)
        originalRequest.headers['Authorization'] = `Bearer ${access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        clearAuth()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

function clearAuth() {
  localStorage.removeItem('garuda_access_token')
  localStorage.removeItem('garuda_refresh_token')
  localStorage.removeItem('garuda_user')
  window.location.href = '/login'
}

// Auth API
export const authApi = {
  login: (username: string, password: string) =>
    axios.post(`${API_BASE_URL}/auth/login`, { username, password }),
  refresh: (refreshToken: string) =>
    axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken }),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
}

// Dashboard API
export const dashboardApi = {
  health: () => api.get('/v1/dashboard/health'),
  recentScans: (limit = 50) => api.get(`/v1/dashboard/recent-scans?limit=${limit}`),
  recentBlocks: (limit = 50) => api.get(`/v1/dashboard/recent-blocks?limit=${limit}`),
  timeline: (interval = 'day', limit = 30) => api.get(`/v1/dashboard/timeline?interval=${interval}&limit=${limit}`),
  engineOutcomes: (limit = 100) => api.get(`/v1/dashboard/engine-outcomes?limit=${limit}`),
  policyHits: (limit = 50) => api.get(`/v1/dashboard/policy-hits?limit=${limit}`),
  session: (id: string) => api.get(`/v1/dashboard/session/${id}`),
  trace: (eventId: string) => api.get(`/v1/dashboard/trace/${eventId}`),
}

// Incidents / Reports API
export const incidentsApi = {
  summary: (start: string, end: string) => api.get(`/v1/reports/incidents/summary?start_date=${start}&end_date=${end}`),
  csv: (start: string, end: string) => api.get(`/v1/reports/incidents/csv?start_date=${start}&end_date=${end}`, { responseType: 'blob' }),
}

// Admin API
export const adminApi = {
  rules: {
    list: () => api.get('/v1/admin/rules'),
    create: (data: any) => api.post('/v1/admin/rules', data),
    update: (id: number, data: any) => api.put(`/v1/admin/rules/${id}`, data),
    delete: (id: number) => api.delete(`/v1/admin/rules/${id}`),
  },
  policies: {
    list: (tenantId?: string) => api.get('/v1/admin/policies', { params: { tenant_id: tenantId } }),
    update: (key: string, data: any) => api.patch(`/v1/admin/policies/${key}`, data),
  },
  tenants: {
    get: (tenantId: string) => api.get(`/v1/admin/tenants/${tenantId}`),
    update: (tenantId: string, data: any) => api.patch(`/v1/admin/tenants/${tenantId}`, data),
  },
  apiKeys: {
    list: (tenantId?: string) => api.get('/v1/admin/api-keys', { params: { tenant_id: tenantId } }),
    create: (data: any) => api.post('/v1/admin/api-keys', data),
    revoke: (id: number) => api.delete(`/v1/admin/api-keys/${id}`),
  },
  users: {
    list: (tenantId?: string) => api.get('/v1/admin/users', { params: { tenant_id: tenantId } }),
    create: (data: any) => api.post('/v1/admin/users', data),
    update: (id: string, data: any) => api.put(`/v1/admin/users/${id}`, data),
    delete: (id: string) => api.delete(`/v1/admin/users/${id}`),
    resetPassword: (id: string, newPassword: string) =>
      api.post(`/v1/admin/users/${id}/reset-password`, { new_password: newPassword }),
  },
}

// Alerts API
export const alertsApi = {
  list: (includeAcknowledged = false) =>
    api.get(`/v1/alerts?include_acknowledged=${includeAcknowledged}`),
  stats: () => api.get('/v1/alerts/stats'),
  acknowledge: (id: string) => api.post(`/v1/alerts/${id}/acknowledge`),
  resolve: (id: string) => api.post(`/v1/alerts/${id}/resolve`),
}

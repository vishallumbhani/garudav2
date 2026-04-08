import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { authApi } from '../services/api'

export interface User {
  id: string
  username: string
  email?: string
  role: 'admin' | 'operator' | 'viewer' | 'auditor'
  tenant_id?: string
  enabled: boolean
}

interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  hasRole: (roles: string[]) => boolean
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('garuda_access_token')
    const storedUser = localStorage.getItem('garuda_user')
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser))
        setIsAuthenticated(true)
        // Silently validate token
        authApi.me()
          .then(res => {
            setUser(res.data)
            localStorage.setItem('garuda_user', JSON.stringify(res.data))
          })
          .catch(() => {
            // Token invalid – clear
            clearSession()
          })
          .finally(() => setIsLoading(false))
      } catch {
        clearSession()
        setIsLoading(false)
      }
    } else {
      setIsLoading(false)
    }
  }, [])

  const clearSession = () => {
    localStorage.removeItem('garuda_access_token')
    localStorage.removeItem('garuda_refresh_token')
    localStorage.removeItem('garuda_user')
    setIsAuthenticated(false)
    setUser(null)
  }

  const login = async (username: string, password: string) => {
    const res = await authApi.login(username, password)
    const { access_token, refresh_token } = res.data
    localStorage.setItem('garuda_access_token', access_token)
    localStorage.setItem('garuda_refresh_token', refresh_token)
    // Fetch full user info
    const meRes = await authApi.me()
    const userData: User = meRes.data
    localStorage.setItem('garuda_user', JSON.stringify(userData))
    setUser(userData)
    setIsAuthenticated(true)
  }

  const logout = useCallback(async () => {
    try { await authApi.logout() } catch {}
    clearSession()
  }, [])

  const hasRole = useCallback((roles: string[]) => {
    if (!user) return false
    if (user.role === 'admin') return true
    return roles.includes(user.role)
  }, [user])

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      user,
      isLoading,
      login,
      logout,
      hasRole,
      isAdmin: user?.role === 'admin',
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

import { useAuth } from '../../hooks/useAuth'
import { LogOut, RefreshCw, Bell, ChevronDown } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const Topbar = () => {
  const { logout, user } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showMenu, setShowMenu] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="bg-gray-900 border-b border-gray-800 px-6 py-0 h-14 flex justify-between items-center shrink-0">
      <h1 className="text-base font-semibold text-white">AI Security Platform</h1>

      <div className="flex items-center gap-3">
        {/* Refresh */}
        <button
          onClick={() => queryClient.invalidateQueries()}
          title="Refresh all data"
          className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition"
        >
          <RefreshCw size={16} />
        </button>

        {/* Alerts bell */}
        <button
          onClick={() => navigate('/alerts')}
          title="Alerts"
          className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition relative"
        >
          <Bell size={16} />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition text-gray-300 hover:text-white"
          >
            <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-xs text-white font-semibold shrink-0">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-xs font-medium leading-none">{user?.username}</p>
              <p className="text-xs text-gray-500 capitalize leading-none mt-0.5">{user?.role}</p>
            </div>
            <ChevronDown size={14} className="text-gray-500" />
          </button>

          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-20 py-1">
                <div className="px-3 py-2 border-b border-gray-700">
                  <p className="text-white text-sm font-medium">{user?.username}</p>
                  <p className="text-gray-500 text-xs">{user?.tenant_id || 'default'}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition"
                >
                  <LogOut size={15} />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

export default Topbar

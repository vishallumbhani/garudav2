import { useAuth } from '../../hooks/useAuth'
import { LogOut, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

const Topbar = () => {
  const { logout, user } = useAuth()
  const queryClient = useQueryClient()
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex justify-between items-center">
      <h1 className="text-xl font-semibold text-white">AI Security Platform</h1>
      <div className="flex items-center gap-4">
        <button onClick={() => queryClient.invalidateQueries()} className="text-gray-400 hover:text-white">
          <RefreshCw size={18} />
        </button>
        <span className="text-sm text-gray-300">{user?.tenant || 'default'}</span>
        <button onClick={logout} className="text-gray-400 hover:text-white">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}
export default Topbar

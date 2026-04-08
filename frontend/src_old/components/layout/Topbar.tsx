import { useAuth } from '../../hooks/useAuth'
import { LogOut, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

const Topbar = () => {
  // We'll get the logout function from props or context
  // For now, use a custom hook if available
  const queryClient = useQueryClient()
  
  // Temporary logout handler – you can pass from App
  const handleLogout = () => {
    localStorage.removeItem('garuda_api_key')
    window.location.href = '/'
  }

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex justify-between items-center">
      <h1 className="text-xl font-semibold text-white">AI Security Platform</h1>
      <div className="flex items-center gap-4">
        <button onClick={() => queryClient.invalidateQueries()} className="text-gray-400 hover:text-white">
          <RefreshCw size={18} />
        </button>
        <button onClick={handleLogout} className="text-gray-400 hover:text-white">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}

export default Topbar

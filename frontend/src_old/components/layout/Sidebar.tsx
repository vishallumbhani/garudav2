import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Scan, AlertTriangle, Calendar, Users, Shield, FileText, Building2, Key, BarChart3 } from 'lucide-react'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/scans', label: 'Scans', icon: Scan },
  { path: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { path: '/timeline', label: 'Timeline', icon: Calendar },
  { path: '/sessions', label: 'Sessions', icon: Users },
  { path: '/policies', label: 'Policies', icon: Shield },
  { path: '/rules', label: 'Rules', icon: FileText },
  { path: '/tenants', label: 'Tenants', icon: Building2 },
  { path: '/api-keys', label: 'API Keys', icon: Key },
  { path: '/reports', label: 'Reports', icon: BarChart3 },
]

const Sidebar = () => {
  return (
    <div className="w-64 bg-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <span className="text-xl font-bold text-white">Garuda</span>
      </div>
      <nav className="flex-1 mt-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors ${
                isActive ? 'bg-gray-700 text-white' : ''
              }`
            }
          >
            <item.icon size={20} />
            <span className="ml-3">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        Version 1.0.0
      </div>
    </div>
  )
}

export default Sidebar

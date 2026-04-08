import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Scan, AlertTriangle, Calendar, Users, Shield, FileText, Building2, Key, BarChart3, ChevronLeft, ChevronRight } from 'lucide-react'

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

const Sidebar = ({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) => (
  <div className={`bg-gray-800 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'} flex flex-col`}>
    <div className="flex items-center justify-between p-4 border-b border-gray-700">
      {!collapsed && <span className="text-xl font-bold text-white">Garuda</span>}
      <button onClick={onToggle} className="text-gray-400 hover:text-white">
        {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
      </button>
    </div>
    <nav className="flex-1 mt-4">
      {navItems.map((item) => (
        <NavLink key={item.path} to={item.path} className={({ isActive }) =>
          `flex items-center px-4 py-3 text-gray-300 hover:bg-gray-700 hover:text-white ${isActive ? 'bg-gray-700 text-white' : ''}`
        }>
          <item.icon size={20} />
          {!collapsed && <span className="ml-3">{item.label}</span>}
        </NavLink>
      ))}
    </nav>
    <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
      {!collapsed && <span>Version 1.0.0</span>}
    </div>
  </div>
)
export default Sidebar

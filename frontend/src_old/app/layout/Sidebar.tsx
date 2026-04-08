import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Scan, AlertTriangle, Calendar, Users, Shield,
  FileText, Building2, Key, BarChart3, ChevronLeft, ChevronRight,
  Bell, UserCog, ShieldCheck
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

const allNavItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: [] },
  { path: '/scans', label: 'Scans', icon: Scan, roles: [] },
  { path: '/incidents', label: 'Incidents', icon: AlertTriangle, roles: [] },
  { path: '/alerts', label: 'Alerts', icon: Bell, roles: [] },
  { path: '/timeline', label: 'Timeline', icon: Calendar, roles: [] },
  { path: '/sessions', label: 'Sessions', icon: Users, roles: [] },
  { path: '/policies', label: 'Policies', icon: Shield, roles: ['admin', 'operator'] },
  { path: '/rules', label: 'Rules', icon: FileText, roles: ['admin', 'operator'] },
  { path: '/tenants', label: 'Tenants', icon: Building2, roles: ['admin'] },
  { path: '/api-keys', label: 'API Keys', icon: Key, roles: ['admin'] },
  { path: '/admin/users', label: 'Users', icon: UserCog, roles: ['admin'] },
  { path: '/reports', label: 'Reports', icon: BarChart3, roles: [] },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
  const { user, hasRole } = useAuth()

  const visibleItems = allNavItems.filter(item =>
    item.roles.length === 0 || hasRole(item.roles)
  )

  return (
    <div className={`bg-gray-900 border-r border-gray-800 transition-all duration-300 ${collapsed ? 'w-16' : 'w-60'} flex flex-col shrink-0`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800 h-14">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
              <ShieldCheck size={15} className="text-white" />
            </div>
            <span className="text-white font-bold text-lg tracking-tight">Garuda</span>
          </div>
        )}
        <button
          onClick={onToggle}
          className={`text-gray-500 hover:text-white transition-colors ${collapsed ? 'mx-auto' : ''}`}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {visibleItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border-r-2 border-blue-500'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              } ${collapsed ? 'justify-center' : ''}`
            }
          >
            <item.icon size={18} className="shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && user && (
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gray-700 rounded-full flex items-center justify-center text-xs text-gray-300 font-semibold shrink-0">
              {user.username[0].toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <p className="text-white text-xs font-medium truncate">{user.username}</p>
              <p className="text-gray-500 text-xs capitalize">{user.role}</p>
            </div>
          </div>
        </div>
      )}
      {!collapsed && (
        <div className="px-4 pb-3 text-xs text-gray-700">v1.0.0</div>
      )}
    </div>
  )
}

export default Sidebar

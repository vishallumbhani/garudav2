import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/api'
import { useState } from 'react'
import { Plus, Pencil, Trash2, KeyRound, Check, X, ShieldCheck, Eye } from 'lucide-react'

const ROLES = ['admin', 'operator', 'viewer', 'auditor']

const roleBadge: Record<string, string> = {
  admin: 'bg-red-900/50 text-red-300 border border-red-800',
  operator: 'bg-orange-900/50 text-orange-300 border border-orange-800',
  viewer: 'bg-blue-900/50 text-blue-300 border border-blue-800',
  auditor: 'bg-purple-900/50 text-purple-300 border border-purple-800',
}

type ModalMode = 'create' | 'edit' | 'reset' | null

interface UserFormData {
  username: string
  password: string
  email: string
  role: string
  tenant_id: string
}

const defaultForm: UserFormData = {
  username: '', password: '', email: '', role: 'viewer', tenant_id: 'default',
}

const UsersPage = () => {
  const queryClient = useQueryClient()
  const [modal, setModal] = useState<ModalMode>(null)
  const [selectedUser, setSelectedUser] = useState<any>(null)
  const [form, setForm] = useState<UserFormData>(defaultForm)
  const [newPassword, setNewPassword] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [toast, setToast] = useState('')

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => adminApi.users.list().then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => adminApi.users.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setModal(null)
      setForm(defaultForm)
      showToast('User created successfully')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: any) => adminApi.users.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setModal(null)
      showToast('User updated')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.users.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setDeleteConfirm(null)
      showToast('User deleted')
    },
  })

  const resetMutation = useMutation({
    mutationFn: ({ id, password }: any) => adminApi.users.resetPassword(id, password),
    onSuccess: () => {
      setModal(null)
      setNewPassword('')
      showToast('Password reset successfully')
    },
  })

  const openCreate = () => { setForm(defaultForm); setModal('create') }
  const openEdit = (user: any) => {
    setSelectedUser(user)
    setForm({ username: user.username, password: '', email: user.email || '', role: user.role, tenant_id: user.tenant_id || 'default' })
    setModal('edit')
  }
  const openReset = (user: any) => { setSelectedUser(user); setNewPassword(''); setModal('reset') }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (modal === 'create') {
      createMutation.mutate(form)
    } else if (modal === 'edit') {
      const { username, password, ...rest } = form
      updateMutation.mutate({ id: selectedUser.id, data: rest })
    }
  }

  return (
    <div className="space-y-5">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-800 border border-green-700 text-green-200 px-4 py-2.5 rounded-lg text-sm shadow-lg flex items-center gap-2">
          <Check size={14} /> {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">User Management</h1>
          <p className="text-gray-500 text-sm mt-0.5">{users.length} user{users.length !== 1 ? 's' : ''} total</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          <Plus size={16} /> New User
        </button>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading users…</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-800/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">User</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Role</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Tenant</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Last Login</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {users.map((user: any) => (
                <tr key={user.id} className="hover:bg-gray-800/30 transition">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center text-xs text-gray-300 font-semibold shrink-0">
                        {user.username[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-white font-medium">{user.username}</p>
                        {user.email && <p className="text-gray-500 text-xs">{user.email}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${roleBadge[user.role] || 'bg-gray-700 text-gray-300'}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs font-mono">{user.tenant_id || 'default'}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${user.enabled ? 'bg-green-900/50 text-green-300 border border-green-800' : 'bg-red-900/50 text-red-300 border border-red-800'}`}>
                      {user.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button onClick={() => openEdit(user)} className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition" title="Edit">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => openReset(user)} className="p-1.5 text-gray-400 hover:text-amber-400 hover:bg-gray-700 rounded-lg transition" title="Reset password">
                        <KeyRound size={14} />
                      </button>
                      <button onClick={() => setDeleteConfirm(user.id)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition" title="Delete">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-600">No users found</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Create/Edit Modal */}
      {(modal === 'create' || modal === 'edit') && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md shadow-2xl">
            <div className="flex justify-between items-center p-5 border-b border-gray-800">
              <h2 className="text-white font-semibold">{modal === 'create' ? 'Create User' : 'Edit User'}</h2>
              <button onClick={() => setModal(null)} className="text-gray-500 hover:text-white"><X size={18} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              {modal === 'create' && (
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Username *</label>
                  <input required value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              )}
              {modal === 'create' && (
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Password *</label>
                  <input required type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Email</label>
                <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Role</label>
                  <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Tenant</label>
                  <input value={form.tenant_id} onChange={e => setForm(f => ({ ...f, tenant_id: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              {modal === 'edit' && (
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.role !== 'disabled'}
                    onChange={() => {}} className="sr-only" />
                  <span className="text-xs text-gray-400">Enable / Disable via Role field above</span>
                </label>
              )}
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setModal(null)}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2 text-sm transition">
                  Cancel
                </button>
                <button type="submit"
                  className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-2 text-sm font-medium transition">
                  {modal === 'create' ? 'Create' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {modal === 'reset' && selectedUser && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-sm shadow-2xl">
            <div className="flex justify-between items-center p-5 border-b border-gray-800">
              <h2 className="text-white font-semibold">Reset Password</h2>
              <button onClick={() => setModal(null)} className="text-gray-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-gray-400 text-sm">Reset password for <span className="text-white font-medium">{selectedUser.username}</span></p>
              <input type="password" placeholder="New password" value={newPassword} onChange={e => setNewPassword(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <div className="flex gap-3">
                <button onClick={() => setModal(null)}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2 text-sm transition">Cancel</button>
                <button
                  onClick={() => resetMutation.mutate({ id: selectedUser.id, password: newPassword })}
                  disabled={!newPassword}
                  className="flex-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition">
                  Reset
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-sm shadow-2xl p-5 space-y-4">
            <h2 className="text-white font-semibold">Confirm Delete</h2>
            <p className="text-gray-400 text-sm">This action cannot be undone. The user will lose all access immediately.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2 text-sm transition">Cancel</button>
              <button onClick={() => deleteMutation.mutate(deleteConfirm)}
                className="flex-1 bg-red-700 hover:bg-red-600 text-white rounded-lg py-2 text-sm font-medium transition">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UsersPage

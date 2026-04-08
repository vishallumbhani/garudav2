import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'

const RulesPage = () => {
  const queryClient = useQueryClient()
  const { data: rules } = useQuery({ queryKey: ['rules'], queryFn: () => adminApi.rules.list().then(r => r.data) })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.rules.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] })
  })
  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'engine', label: 'Engine' },
    { key: 'name', label: 'Name' },
    { key: 'action', label: 'Action' },
    { key: 'enabled', label: 'Enabled', render: (v: boolean) => v ? 'Yes' : 'No' }
  ]
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Rules</h1>
      <div className="bg-gray-800 rounded-lg p-4">
        <DataTable columns={columns} data={rules || []} />
      </div>
    </div>
  )
}
export default RulesPage
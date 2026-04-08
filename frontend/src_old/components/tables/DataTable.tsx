import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, Download, Search, X } from 'lucide-react'

export interface Column {
  key: string
  label: string
  sortable?: boolean
  render?: (value: any, row: any) => React.ReactNode
  className?: string
}

interface DataTableProps {
  columns: Column[]
  data: any[]
  onRowClick?: (row: any) => void
  searchable?: boolean
  exportable?: boolean
  exportFilename?: string
  emptyMessage?: string
  maxHeight?: string
}

function escapeCSV(val: any): string {
  if (val === null || val === undefined) return ''
  const str = String(val)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

const DataTable = ({
  columns,
  data,
  onRowClick,
  searchable = false,
  exportable = false,
  exportFilename = 'export',
  emptyMessage = 'No data',
  maxHeight,
}: DataTableProps) => {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [search, setSearch] = useState('')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const filtered = useMemo(() => {
    if (!search.trim()) return data
    const q = search.toLowerCase()
    return data.filter(row =>
      columns.some(col => String(row[col.key] ?? '').toLowerCase().includes(q))
    )
  }, [data, search, columns])

  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    return [...filtered].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (av === bv) return 0
      const cmp = av < bv ? -1 : 1
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortKey, sortDir])

  const handleExport = () => {
    const header = columns.map(c => escapeCSV(c.label)).join(',')
    const rows = sorted.map(row =>
      columns.map(col => escapeCSV(row[col.key])).join(',')
    )
    const csv = [header, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${exportFilename}_${new Date().toISOString().slice(0,10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const SortIcon = ({ col }: { col: Column }) => {
    if (!col.sortable) return null
    if (sortKey !== col.key) return <ChevronsUpDown size={13} className="text-gray-600 ml-1" />
    return sortDir === 'asc'
      ? <ChevronUp size={13} className="text-blue-400 ml-1" />
      : <ChevronDown size={13} className="text-blue-400 ml-1" />
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      {(searchable || exportable) && (
        <div className="flex items-center gap-3 justify-between">
          {searchable ? (
            <div className="relative flex-1 max-w-xs">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder="Search…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-8 pr-8 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
                  <X size={14} />
                </button>
              )}
            </div>
          ) : <div />}
          {exportable && (
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 hover:text-white rounded-lg text-xs font-medium transition"
            >
              <Download size={13} /> Export CSV
            </button>
          )}
        </div>
      )}

      {/* Table */}
      <div className={`overflow-x-auto rounded-lg border border-gray-800 ${maxHeight ? `max-h-[${maxHeight}] overflow-y-auto` : ''}`}>
        {sorted.length === 0 ? (
          <div className="py-10 text-center text-gray-600 text-sm">{search ? 'No results match your search' : emptyMessage}</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-gray-800/60 sticky top-0">
              <tr>
                {columns.map(col => (
                  <th
                    key={col.key}
                    onClick={() => col.sortable && handleSort(col.key)}
                    className={`px-4 py-2.5 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap ${col.sortable ? 'cursor-pointer hover:text-white select-none' : ''} ${col.className || ''}`}
                  >
                    <span className="flex items-center">
                      {col.label}
                      <SortIcon col={col} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {sorted.map((row, idx) => (
                <tr
                  key={idx}
                  onClick={() => onRowClick?.(row)}
                  className={`transition-colors ${onRowClick ? 'cursor-pointer hover:bg-gray-800/40' : 'hover:bg-gray-800/20'}`}
                >
                  {columns.map(col => (
                    <td key={col.key} className={`px-4 py-2.5 text-gray-300 ${col.className || ''}`}>
                      {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer count */}
      {sorted.length > 0 && (
        <p className="text-xs text-gray-600">
          {search ? `${sorted.length} of ${data.length} rows` : `${sorted.length} rows`}
        </p>
      )}
    </div>
  )
}

export default DataTable

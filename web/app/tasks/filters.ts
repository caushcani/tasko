import type { FilterField } from '@/lib/table/filter-types'

export const TASK_FILTERS: FilterField[] = [
  {
    field: 'state',
    label: 'State',
    type: 'select',
    options: [
      { label: 'Queued', value: 'queued' },
      { label: 'Started', value: 'started' },
      { label: 'Success', value: 'success' },
      { label: 'Failure', value: 'failure' },
      { label: 'Retry', value: 'retry' },
    ],
  },
  { field: 'queue', label: 'Queue', type: 'text', placeholder: 'Queue name…' },
  { field: 'worker_id', label: 'Worker', type: 'text', placeholder: 'Worker id…' },
]

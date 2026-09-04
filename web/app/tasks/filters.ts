// Declared as data, mirroring the backend's TASK_LIST_SPEC.filterable_fields
// (packages/tasko-core/.../modules/tasks/models.py). `field` must match those
// names exactly — the FilterBar's values are sent straight through as the
// route's `state` / `queue` / `worker_id` query params.

import type { FilterField } from '@/lib/table/filter-types'

export const TASK_FILTERS: FilterField[] = [
  { field: 'name', label: 'Name', type: 'text', placeholder: 'Task name…' },
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

// Declared as data, mirroring the backend's TASK_LIST_SPEC.filterable_fields
// (packages/tasko-core/.../modules/tasks/models.py). `field` must match those
// names exactly — the FilterBar's values are sent straight through as the
// route's `state` / `queue` / `worker_id` query params.

import type { FilterField } from '@/lib/table/filter-types'

export const TASK_FILTERS: FilterField[] = [
  // No "name" filter here on purpose: the backend's `name` filter is exact-
  // match (see filtering.py — non-list values become `column == value`), so
  // a text box inviting partial typing would silently return nothing for
  // anything but the full task name. The search box above (`q`) already does
  // substring matching across id/name/traceback — that's the "find by name"
  // affordance. Add one back only alongside a real substring filter type.
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

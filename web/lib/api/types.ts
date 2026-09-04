// Shared response envelope — mirrors tasko-core's
// `tasko_core.modules.common.pagination.PaginatedResponse`.

export interface PaginatedResponse<T> {
  items: T[]
  total_count: number
  offset: number
  limit: number
}

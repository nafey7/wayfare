/**
 * Standard API error response
 */
export interface ApiError {
  detail: string | ValidationError[];
  statusCode?: number;
}

/**
 * Validation error from Pydantic
 */
export interface ValidationError {
  loc: string[];
  msg: string;
  type: string;
}

/**
 * Generic success response
 */
export interface SuccessResponse {
  message: string;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

/**
 * API query params for pagination
 */
export interface PaginationParams {
  page?: number;
  limit?: number;
}

/**
 * Sort options
 */
export interface SortParams {
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

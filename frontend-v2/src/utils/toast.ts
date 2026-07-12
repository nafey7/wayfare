import { toast as reactToast, ToastOptions } from 'react-toastify';

/**
 * Default toast configuration matching the ToastContainer setup in main.tsx
 */
const defaultToastOptions: ToastOptions = {
  position: 'top-right',
  autoClose: 5000,
  hideProgressBar: false,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  theme: 'colored',
};

/**
 * Show an error toast notification
 * @param message - Error message to display
 * @param options - Optional toast configuration (will be merged with defaults)
 */
export function showErrorToast(message: string, options?: ToastOptions) {
  return reactToast.error(message, {
    ...defaultToastOptions,
    ...options,
  });
}

/**
 * Show a success toast notification
 * @param message - Success message to display
 * @param options - Optional toast configuration (will be merged with defaults)
 */
export function showSuccessToast(message: string, options?: ToastOptions) {
  return reactToast.success(message, {
    ...defaultToastOptions,
    ...options,
  });
}

/**
 * Show an info toast notification
 * @param message - Info message to display
 * @param options - Optional toast configuration (will be merged with defaults)
 */
export function showInfoToast(message: string, options?: ToastOptions) {
  return reactToast.info(message, {
    ...defaultToastOptions,
    ...options,
  });
}

/**
 * Show a warning toast notification
 * @param message - Warning message to display
 * @param options - Optional toast configuration (will be merged with defaults)
 */
export function showWarningToast(message: string, options?: ToastOptions) {
  return reactToast.warning(message, {
    ...defaultToastOptions,
    ...options,
  });
}

/**
 * Extract user-friendly error message from API error
 * Handles RTK Query errors and standard API errors
 * @param error - Error object from API call
 * @param defaultMessage - Default message if error cannot be parsed
 * @returns User-friendly error message
 */
export function extractErrorMessage(
  error: unknown,
  defaultMessage = 'An error occurred. Please try again.'
): string {
  // RTK Query error structure
  if (error && typeof error === 'object') {
    // Check for RTK Query error with data.detail
    if ('data' in error && error.data && typeof error.data === 'object') {
      if ('detail' in error.data && typeof error.data.detail === 'string') {
        return error.data.detail;
      }
      // Check for message property
      if ('message' in error.data && typeof error.data.message === 'string') {
        return error.data.message;
      }
    }

    // Check for status-specific messages
    if ('status' in error && typeof error.status === 'number') {
      const status = error.status;
      if (status === 401) {
        return 'You are not authorized. Please sign in.';
      }
      if (status === 403) {
        return 'You do not have permission to perform this action.';
      }
      if (status === 404) {
        return 'The requested resource was not found.';
      }
      if (status === 410) {
        return 'This resource is no longer available. Please try again.';
      }
      if (status === 429) {
        return 'Too many requests. Please try again later.';
      }
      if (status >= 500) {
        return 'Server error. Please try again later.';
      }
    }

    // Check for standard Error object
    if (error instanceof Error) {
      return error.message;
    }
  }

  // Check for string errors
  if (typeof error === 'string') {
    return error;
  }

  return defaultMessage;
}

/**
 * Show error toast from API error
 * Automatically extracts user-friendly message from error object
 * @param error - Error object from API call
 * @param defaultMessage - Default message if error cannot be parsed
 * @param options - Optional toast configuration
 */
export function showErrorToastFromError(
  error: unknown,
  defaultMessage = 'An error occurred. Please try again.',
  options?: ToastOptions
) {
  const message = extractErrorMessage(error, defaultMessage);
  return showErrorToast(message, options);
}

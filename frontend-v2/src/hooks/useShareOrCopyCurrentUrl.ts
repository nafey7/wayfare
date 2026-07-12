import { useCallback } from 'react';
import { showErrorToast } from '@/utils/toast';

export interface UseShareOrCopyCurrentUrlOptions {
  /** Passed to `navigator.share` when available. */
  title?: string;
  /**
   * When set, used for the clipboard fallback (and optional `text` on `navigator.share`)
   * instead of the raw page URL — useful for copy-friendly labels or preformatted snippets.
   */
  text?: string;
}

/**
 * Shares the current page URL via Web Share API when supported; otherwise copies to clipboard.
 * Swallows user-cancel (AbortError) and shows a toast on other failures.
 */
export function useShareOrCopyCurrentUrl(
  options: UseShareOrCopyCurrentUrlOptions = {},
): () => void {
  const { title: titleOption, text } = options;

  return useCallback(() => {
    void (async () => {
      const shareUrl = window.location.href;
      const clipboardPayload = text ?? shareUrl;
      const shareTitle =
        titleOption ?? (typeof document !== 'undefined' ? document.title : '');
      try {
        if (navigator.share) {
          await navigator.share({
            title: shareTitle,
            url: shareUrl,
            ...(text !== undefined ? { text } : {}),
          });
        } else {
          await navigator.clipboard.writeText(clipboardPayload);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        showErrorToast(
          'Could not share or copy the link. Copy the address from your browser bar if needed.',
        );
      }
    })();
  }, [titleOption, text]);
}

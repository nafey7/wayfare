import { useEffect, useRef } from 'react';

import { useClaimGuestChatMutation } from '@/api';
import {
  getPublicChatId,
  getPublicChatSessionId,
  clearPublicChatSession,
} from '@/features/chat/utils/publicChatSession';
import { clearGuestChatTranscript } from '@/features/chat/utils/publicChatGuestTranscript';
import { setChatId } from '@/store/slices/chatSlice';
import type { AppDispatch } from '@/store';
import type { ClaimChatStatus } from '@/types/chat';
import { trackEvent } from '@/utils/gtm';

const TERMINAL_SUCCESS_STATUSES: readonly ClaimChatStatus[] = [
  'claimed',
  'already_claimed',
] as const;

interface UseGuestChatClaimArgs {
  dispatch: AppDispatch;
  isAuthenticated: boolean;
  publicChatEnabled: boolean;
  configLoaded: boolean;
}

/**
 * Post-auth one-shot: re-own the guest chat thread (if any) for the freshly
 * authenticated user, then clear guest localStorage keys.
 *
 * Mirrors the lifecycle of ``PublicChatPostAuthConversionTracker``: runs once
 * per session via a ref guard; failure never blocks login (falls back to the
 * pre-claim behaviour where the next message starts a fresh chat_id).
 */
export function useGuestChatClaim({
  dispatch,
  isAuthenticated,
  publicChatEnabled,
  configLoaded,
}: UseGuestChatClaimArgs): void {
  const didClaimRef = useRef(false);
  const [claimMutation] = useClaimGuestChatMutation();

  useEffect(() => {
    if (!isAuthenticated || !publicChatEnabled || !configLoaded) return;
    if (didClaimRef.current) return;

    const sessionId = getPublicChatSessionId();
    const chatId = getPublicChatId();
    if (!sessionId || !chatId) {
      didClaimRef.current = true;
      return;
    }

    didClaimRef.current = true;

    claimMutation({ body: { chat_id: chatId }, sessionId })
      .unwrap()
      .then((response) => {
        const isSuccess =
          TERMINAL_SUCCESS_STATUSES.includes(response.status) &&
          Boolean(response.chat_id);
        if (isSuccess && response.chat_id) {
          dispatch(setChatId(response.chat_id));
          clearPublicChatSession();
          clearGuestChatTranscript();
          trackEvent('chat_claim.completed', { status: response.status });
        } else if (response.status === 'nothing_to_claim') {
          // The guest chat_id has no backing rows (deleted thread, wiped DB,
          // dev/test data mismatch). Don't pin the authed user to an orphan
          // chat_id — drop it so the next message starts a fresh thread, and
          // clear guest keys so we don't retry the same doomed lookup.
          dispatch(setChatId(null));
          clearPublicChatSession();
          clearGuestChatTranscript();
          trackEvent('chat_claim.rejected', { status: response.status });
        } else {
          // Server told us the thread can't be claimed (e.g. age/cap reject
          // returned as 4xx ends up in the catch branch). Treat as no-op.
          dispatch(setChatId(null));
          clearPublicChatSession();
          trackEvent('chat_claim.rejected', { status: response.status });
        }
      })
      .catch((err: unknown) => {
        // Failure: keep transcript visible via existing lifecycle fallback,
        // but null the chat_id so the next authed message starts cleanly.
        // Leave guest keys in place on transient/server errors so a future
        // reload can retry (one-shot is enforced by didClaimRef so the same
        // browser session won't loop).
        const status =
          typeof err === 'object' && err !== null && 'status' in err
            ? (err as { status: unknown }).status
            : undefined;
        if (typeof status === 'number' && status >= 400 && status < 500) {
          // 4xx: server rejected the claim (fingerprint mismatch, too old,
          // owned by someone else). Clear the guest keys so we don't keep
          // sending the same doomed request.
          dispatch(setChatId(null));
          clearPublicChatSession();
        } else {
          dispatch(setChatId(null));
        }
        trackEvent('chat_claim.failed', {
          status: typeof status === 'number' ? status : 'unknown',
        });
        console.warn('chat_claim.failed', err);
      });
  }, [isAuthenticated, publicChatEnabled, configLoaded, claimMutation, dispatch]);
}

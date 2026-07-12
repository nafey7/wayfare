import { useState, useEffect, useCallback, useMemo } from 'react';
import type { ChatMessage, ChatSuggestion } from '@/types/chat';

/**
 * Derives the active suggestions from the latest bot message and
 * hides them after the user sends a message (waiting for bot reply)
 * or after the user clicks a suggestion.
 * Typing alone does NOT hide suggestions.
 */
export function useActiveSuggestions(messages: ChatMessage[]) {
  const [dismissedForId, setDismissedForId] = useState<string | null>(null);

  const latestBotMsg = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg && msg.from === 'bot' && msg.type !== 'typing') return msg;
    }
    return null;
  }, [messages]);

  const rawSuggestions: ChatSuggestion[] = latestBotMsg?.content?.suggestions ?? [];
  const sourceId = latestBotMsg?._id ?? null;

  const lastMsg = messages[messages.length - 1];
  const waitingForReply =
    lastMsg?.from === 'user' || lastMsg?.type === 'typing';

  // Reset dismissal when the latest bot message identity changes
  useEffect(() => {
    setDismissedForId(null);
  }, [sourceId]);

  const isDismissed = dismissedForId === sourceId;

  const activeSuggestions: ChatSuggestion[] =
    isDismissed || waitingForReply ? [] : rawSuggestions;

  const dismiss = useCallback(() => {
    if (sourceId) setDismissedForId(sourceId);
  }, [sourceId]);

  return { activeSuggestions, dismiss };
}

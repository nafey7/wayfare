import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import type { ChatMessage } from '@/types/chat';
import { shouldSkipRedundantUrlPromptSend } from '@/features/chat/utils/urlPromptChatHandoff';

export interface UseUrlPromptSendOptions {
  messagesLoaded: boolean;
  messages: ChatMessage[];
  publicChatEnabled: boolean;
  sendMessage: (text: string) => void | Promise<void>;
  /** Floating widget opens the panel before sending; standalone full-page chat omits this. */
  openChat?: () => void;
}

/**
 * Reads `?prompt=` from the URL and sends it through the chat pipeline when history is ready,
 * then strips the query param. Shared by floating {@link ChatBot} and standalone {@link ChatPanel}.
 *
 * Tracks the last-processed prompt string (not a one-shot boolean) so that repeated navigations
 * to `?prompt=<new value>` on the same mounted component — e.g. NavbarChatSearch used multiple
 * times while already on /chat — each trigger a fresh send.
 */
export function useUrlPromptSend({
  messagesLoaded,
  messages,
  publicChatEnabled,
  sendMessage,
  openChat,
}: UseUrlPromptSendOptions): void {
  const [searchParams, setSearchParams] = useSearchParams();
  const [pendingUrlPrompt, setPendingUrlPrompt] = useState<string | null>(null);
  const lastProcessedPromptRef = useRef<string | null>(null);
  const urlPromptSentRef = useRef(false);

  useEffect(() => {
    const prompt = searchParams.get('prompt');
    const trimmed = prompt?.trim() ?? '';
    // Identical prompt values are intentionally de-duped (rapid double-mount guard).
    // A different value always triggers a fresh send, even on the same mounted component.
    if (trimmed && trimmed !== lastProcessedPromptRef.current) {
      lastProcessedPromptRef.current = trimmed;
      urlPromptSentRef.current = false;
      setPendingUrlPrompt(trimmed);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!pendingUrlPrompt || !messagesLoaded || urlPromptSentRef.current) return;

    if (shouldSkipRedundantUrlPromptSend(publicChatEnabled, messages, pendingUrlPrompt)) {
      urlPromptSentRef.current = true;
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('prompt');
      setSearchParams(nextParams, { replace: true });
      setPendingUrlPrompt(null);
      return;
    }

    urlPromptSentRef.current = true;
    openChat?.();
    void sendMessage(pendingUrlPrompt);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('prompt');
    setSearchParams(nextParams, { replace: true });
    setPendingUrlPrompt(null);
  }, [
    pendingUrlPrompt,
    messagesLoaded,
    messages,
    publicChatEnabled,
    sendMessage,
    openChat,
    searchParams,
    setSearchParams,
  ]);
}

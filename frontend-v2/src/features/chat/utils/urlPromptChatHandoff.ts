import type { ChatMessage } from '@/types/chat';

/**
 * Skip auto-send of `?prompt=` when the thread already contains a matching user message
 * (e.g. duplicate from another entry path). Used for both public and JWT chat.
 */
export function shouldSkipRedundantUrlPromptSend(
  publicChatEnabled: boolean,
  messages: ChatMessage[],
  prompt: string
): boolean {
  if (!publicChatEnabled) return false;
  const t = prompt.trim();
  if (!t) return false;
  return messages.some((m) => {
    if (m.from !== 'user' || m.type !== 'message') return false;
    const text = m.content?.messages?.[0]?.text?.trim();
    return text === t;
  });
}

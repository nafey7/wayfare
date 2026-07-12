import { useRef, useEffect, useCallback } from 'react';
import type { ChatMessage } from '@/types/chat';

interface UseChatScrollOptions {
  messages: ChatMessage[];
  autoScroll: boolean;
  isOpen: boolean;
}

interface UseChatScrollReturn {
  containerRef: React.RefObject<HTMLDivElement>;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  scrollToBottom: () => void;
  scrollToTop: () => void;
}

/**
 * Hook to manage chat scroll behavior
 *
 * @param options - Configuration options
 * @returns Refs and scroll functions
 */
export function useChatScroll({
  messages,
  autoScroll,
  isOpen,
}: UseChatScrollOptions): UseChatScrollReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const scrollToTop = useCallback(() => {
    containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (autoScroll && isOpen && messages.length > 0) {
      // Small delay to ensure DOM has updated
      const timer = setTimeout(() => {
        scrollToBottom();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages, autoScroll, isOpen, scrollToBottom]);

  // Scroll to bottom when chat opens
  useEffect(() => {
    if (isOpen && autoScroll) {
      const timer = setTimeout(() => {
        scrollToBottom();
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [isOpen, autoScroll, scrollToBottom]);

  return {
    containerRef,
    messagesEndRef,
    scrollToBottom,
    scrollToTop,
  };
}

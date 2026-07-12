import { describe, it, expect, vi } from 'vitest';
import { render, act } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import type { ChatMessage } from '@/types/chat';
import { useUrlPromptSend } from './useUrlPromptSend';

function TestHook({ sendMessage }: { sendMessage: (t: string) => void }) {
  useUrlPromptSend({
    messagesLoaded: true,
    messages: [] as ChatMessage[],
    publicChatEnabled: false,
    sendMessage,
  });
  return null;
}

function setup(sendMessage: (t: string) => void, initialPath = '/') {
  const router = createMemoryRouter([{ path: '/', element: <TestHook sendMessage={sendMessage} /> }], {
    initialEntries: [initialPath],
  });
  render(<RouterProvider router={router} />);
  return router;
}

describe('useUrlPromptSend', () => {
  it('sends the prompt from the URL on mount', () => {
    const sendMessage = vi.fn();
    setup(sendMessage, '/?prompt=hello');
    expect(sendMessage).toHaveBeenCalledWith('hello');
    expect(sendMessage).toHaveBeenCalledTimes(1);
  });

  it('sends a second distinct prompt when the URL changes on the same mounted component', async () => {
    const sendMessage = vi.fn();
    const router = setup(sendMessage, '/?prompt=first');
    expect(sendMessage).toHaveBeenCalledWith('first');

    await act(async () => {
      await router.navigate('/?prompt=second');
    });

    expect(sendMessage).toHaveBeenCalledWith('second');
    expect(sendMessage).toHaveBeenCalledTimes(2);
  });

  it('does not re-send the same prompt value (rapid double-mount guard)', async () => {
    const sendMessage = vi.fn();
    const router = setup(sendMessage, '/?prompt=foo');
    expect(sendMessage).toHaveBeenCalledTimes(1);

    await act(async () => {
      await router.navigate('/?prompt=foo');
    });

    expect(sendMessage).toHaveBeenCalledTimes(1);
  });

  it('trims whitespace before comparing and sending', () => {
    const sendMessage = vi.fn();
    setup(sendMessage, '/?prompt=%20hello%20');
    expect(sendMessage).toHaveBeenCalledWith('hello');
  });

  it('does not send when prompt is empty', () => {
    const sendMessage = vi.fn();
    setup(sendMessage, '/?prompt=');
    expect(sendMessage).not.toHaveBeenCalled();
  });
});

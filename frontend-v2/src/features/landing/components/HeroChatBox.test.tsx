import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';

import { mantineTheme } from '@/theme';
import { HeroChatBox } from './HeroChatBox';

function renderHeroChatBox(props: Partial<Parameters<typeof HeroChatBox>[0]> = {}) {
  const onSubmit = props.onSubmit ?? vi.fn();
  const utils = render(
    <MantineProvider theme={mantineTheme}>
      <HeroChatBox onSubmit={onSubmit} {...props} />
    </MantineProvider>,
  );
  return { ...utils, onSubmit };
}

describe('HeroChatBox', () => {
  it('calls onSubmit with the trimmed value when Enter is pressed', async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderHeroChatBox();

    const input = screen.getByRole('textbox', { name: /chat with voya ai/i });
    await user.type(input, '  Trip to Tokyo  ');
    await user.keyboard('{Enter}');

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith('Trip to Tokyo');
  });

  it('does not call onSubmit when the input is empty or whitespace-only', async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderHeroChatBox();

    const input = screen.getByRole('textbox', { name: /chat with voya ai/i });

    // Pressing Enter on an empty input is a no-op.
    input.focus();
    await user.keyboard('{Enter}');
    expect(onSubmit).not.toHaveBeenCalled();

    // Whitespace-only is also a no-op.
    await user.type(input, '     ');
    await user.keyboard('{Enter}');
    expect(onSubmit).not.toHaveBeenCalled();

    // Clicking the send button on whitespace stays a no-op.
    const sendButton = screen.getByRole('button', { name: /send to voya ai/i });
    await user.click(sendButton);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onSubmit when the send button is clicked', async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderHeroChatBox();

    const input = screen.getByRole('textbox', { name: /chat with voya ai/i });
    await user.type(input, '5 days in Lisbon');

    const sendButton = screen.getByRole('button', { name: /send to voya ai/i });
    await user.click(sendButton);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith('5 days in Lisbon');
  });

  it('sets type="button" on the send button so it cannot submit an outer form', () => {
    renderHeroChatBox();
    const sendButton = screen.getByRole('button', { name: /send to voya ai/i });
    expect(sendButton).toHaveAttribute('type', 'button');
  });

  it('wires the provided dom ids to the input and send button', () => {
    renderHeroChatBox({
      domIds: { input: 'landing-test-input', sendButton: 'landing-test-send' },
    });

    expect(screen.getByRole('textbox', { name: /chat with voya ai/i })).toHaveAttribute(
      'id',
      'landing-test-input',
    );
    expect(screen.getByRole('button', { name: /send to voya ai/i })).toHaveAttribute(
      'id',
      'landing-test-send',
    );
  });
});

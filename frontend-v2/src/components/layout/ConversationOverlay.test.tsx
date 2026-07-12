import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { ConversationMeta } from '@/types/chat';

vi.mock('@/features/chat/components/ConversationSidebar', () => ({
  ConversationSidebar: () => <div data-testid="conversation-sidebar" />,
}));

import { ConversationOverlay } from './LayoutWithChat';

const noop = vi.fn();

const defaultProps = {
  conversations: [] as ConversationMeta[],
  activeChatId: null,
  onClose: noop,
  onSelect: noop,
  onNewChat: noop,
  onRename: noop,
  onDelete: noop,
};

function renderOverlay(
  variant: 'desktop' | 'mobile' = 'desktop',
  overrides: Partial<typeof defaultProps> = {}
) {
  return render(
    <MantineProvider theme={mantineTheme}>
      <div style={{ position: 'relative' }}>
        <ConversationOverlay {...defaultProps} {...overrides} variant={variant} />
      </div>
    </MantineProvider>
  );
}

describe('ConversationOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ARIA semantics', () => {
    it('renders a dialog with aria-modal and aria-label', () => {
      renderOverlay();
      const dialog = screen.getByRole('dialog');
      expect(dialog.getAttribute('aria-modal')).toBe('true');
      expect(dialog.getAttribute('aria-label')).toBe('Conversations');
    });

    it('renders the backdrop with aria-hidden', () => {
      renderOverlay();
      expect(document.querySelector('[aria-hidden="true"]')).not.toBeNull();
    });
  });

  describe('backdrop-click → onClose', () => {
    it('calls onClose when the backdrop is clicked', async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      renderOverlay('desktop', { onClose });

      const backdrop = document.querySelector('[aria-hidden="true"]') as HTMLElement;
      await user.click(backdrop);

      expect(onClose).toHaveBeenCalledOnce();
    });

    it('does not call onClose when the panel is clicked', async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      renderOverlay('desktop', { onClose });

      await user.click(screen.getByTestId('conversation-sidebar'));

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('ConversationSidebar wiring', () => {
    it('renders ConversationSidebar inside the dialog', () => {
      renderOverlay();
      expect(screen.getByTestId('conversation-sidebar')).toBeDefined();
    });
  });
});

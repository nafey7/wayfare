import { ActionIcon, Box, Tooltip } from '@mantine/core';
import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectChatConfig,
  selectFeedbackSubmitted,
  selectChatId,
  setFeedbackSubmitted,
} from '@/store/slices/chatSlice';
import { useSubmitFeedbackMutation } from '@/api';
import { trackEvent } from '@/utils/gtm';

interface FeedbackButtonsProps {
  messageId: string;
}

export function FeedbackButtons({ messageId }: FeedbackButtonsProps) {
  const dispatch = useAppDispatch();
  const config = useAppSelector(selectChatConfig);
  const feedbackSubmitted = useAppSelector(selectFeedbackSubmitted);
  const chatId = useAppSelector(selectChatId);
  const [submitFeedback] = useSubmitFeedbackMutation();

  // Don't render if feedback is disabled or no messageId
  if (!config.chatFeedbackEnabled || !messageId) {
    return null;
  }

  const currentFeedback = feedbackSubmitted[messageId];

  const handleFeedback = async (feedbackType: 'thumbs_up' | 'thumbs_down') => {
    // Don't allow changing feedback once submitted
    if (currentFeedback) {
      return;
    }

    // Update local state immediately
    dispatch(setFeedbackSubmitted({ messageId, feedbackType }));

    trackEvent('chat_feedback_submitted', {
      feedback_type: feedbackType,
      chat_id: chatId ?? undefined,
      message_id: messageId,
    });

    // Submit to backend
    try {
      await submitFeedback({
        message_id: messageId,
        chat_id: chatId || undefined,
        feedback_type: feedbackType,
      });
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const isUp = currentFeedback === 'thumbs_up';
  const isDown = currentFeedback === 'thumbs_down';

  return (
    <Box
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        marginTop: 4,
        opacity: currentFeedback ? 1 : 0.6,
        transition: 'opacity 0.2s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.opacity = '1';
      }}
      onMouseLeave={(e) => {
        if (!currentFeedback) e.currentTarget.style.opacity = '0.6';
      }}
    >
      <Tooltip label={isUp ? 'Thanks for your feedback!' : 'Helpful'} withinPortal>
        {/* span wrapper: Mantine Tooltip does not fire on natively disabled elements. */}
        <span style={{ display: 'inline-flex' }}>
          <ActionIcon
            size="sm"
            variant="subtle"
            onClick={() => handleFeedback('thumbs_up')}
            disabled={!!currentFeedback}
            aria-label="Thumbs up"
            styles={{
              root: {
                padding: 4,
                color: isUp ? 'var(--mantine-color-green-7)' : 'var(--mantine-color-dimmed)',
                '&:hover': {
                  color: 'var(--mantine-color-green-7)',
                  backgroundColor: 'var(--mantine-color-green-1)',
                },
                '&[data-disabled]': {
                  color: isUp ? 'var(--mantine-color-green-7)' : 'var(--mantine-color-gray-5)',
                  opacity: 1,
                },
              },
            }}
          >
            <ThumbsUp size={16} fill={isUp ? 'currentColor' : 'none'} />
          </ActionIcon>
        </span>
      </Tooltip>

      <Tooltip label={isDown ? 'Thanks for your feedback!' : 'Not helpful'} withinPortal>
        <span style={{ display: 'inline-flex' }}>
          <ActionIcon
            size="sm"
            variant="subtle"
            onClick={() => handleFeedback('thumbs_down')}
            disabled={!!currentFeedback}
            aria-label="Thumbs down"
            styles={{
              root: {
                padding: 4,
                color: isDown ? 'var(--mantine-color-red-7)' : 'var(--mantine-color-dimmed)',
                '&:hover': {
                  color: 'var(--mantine-color-red-7)',
                  backgroundColor: 'var(--mantine-color-red-1)',
                },
                '&[data-disabled]': {
                  color: isDown ? 'var(--mantine-color-red-7)' : 'var(--mantine-color-gray-5)',
                  opacity: 1,
                },
              },
            }}
          >
            <ThumbsDown size={16} fill={isDown ? 'currentColor' : 'none'} />
          </ActionIcon>
        </span>
      </Tooltip>
    </Box>
  );
}

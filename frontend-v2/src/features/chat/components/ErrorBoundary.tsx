import { Component, type ReactNode, type ErrorInfo } from 'react';
import { Avatar, Box, Button, Text } from '@mantine/core';
import { chatConfig } from '../styles/chatTheme';

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

/**
 * Error boundary for chat components
 * Catches rendering errors and displays a friendly message instead of crashing
 */
export class ChatErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ChatErrorBoundary caught an error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: undefined });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      const message =
        this.props.fallbackMessage || 'Something went wrong displaying this content.';

      return (
        <Box style={{ marginBottom: 16, gap: 8 }}>
          <Box
            style={{
              display: 'flex',
              justifyContent: 'flex-start',
              alignItems: 'flex-end',
              gap: 8,
              marginBottom: 16,
            }}
          >
            <Avatar src={chatConfig.avatars.bot} alt="Bot" size={32} radius="xl" />
            <Box
              style={{
                backgroundColor: 'white',
                borderRadius: '8px 8px 8px 0px',
                boxShadow:
                  '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                padding: 10,
                marginBottom: 8,
              }}
            >
              <Text c="red" mb={8}>{message}</Text>
              <Button
                variant="outline"
                size="xs"
                onClick={this.handleRetry}
              >
                Try again
              </Button>
            </Box>
          </Box>
        </Box>
      );
    }

    return this.props.children;
  }
}

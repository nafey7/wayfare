import { Box } from '@mantine/core';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

export function renderMarkdown(text: string): string {
  const html = marked.parse(text, { async: false, breaks: true, gfm: true }) as string;
  return DOMPurify.sanitize(html);
}

export function TypingIndicator() {
  return (
    <Box style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0', minWidth: 52 }}>
      {[0, 1, 2].map((i) => (
        <Box
          key={i}
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: 'var(--mantine-color-brand-6)',
            animation: 'voya-bounce 1.4s infinite ease-in-out both',
            animationDelay: `${i * 0.16}s`,
          }}
        />
      ))}
    </Box>
  );
}

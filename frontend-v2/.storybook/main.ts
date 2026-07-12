import type { StorybookConfig } from '@storybook/react-vite';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: [
    '@storybook/addon-docs',
    '@storybook/addon-vitest',
    '@storybook/addon-a11y',
    '@storybook/addon-themes',
    '@storybook/addon-mcp',
  ],
  framework: '@storybook/react-vite',
  viteFinal: async (config) => {
    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': resolve(__dirname, '../src'),
    };
    // Dedupe MUI packages to prevent ThemeProvider context duplication
    config.resolve.dedupe = [
      ...(config.resolve.dedupe || []),
      '@mui/material',
      '@mui/system',
      '@mui/private-theming',
      '@emotion/react',
      '@emotion/styled',
      '@mantine/core',
      'react',
      'react-dom',
    ];
    return config;
  },
};

export default config;

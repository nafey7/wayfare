import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';

import authReducer from '@/store/slices/authSlice';
import type { User } from '@/types/auth';
import { AdminDiscountsPage } from './AdminDiscountsPage';

const refetch = vi.fn();
const createTrigger = vi.fn();

vi.mock('@/api/adminDiscountsApi', () => ({
  useListAdminDiscountBatchesQuery: vi.fn(() => ({
    data: {
      batches: [
        {
          batchId: 'batch-uuid-1',
          source: 'G2A_test',
          total: 3,
          used: 0,
          reserved: 0,
          active: 3,
          expired: 0,
          disabled: 0,
          createdAt: '2026-01-01T00:00:00.000Z',
          totalAmountCents: 15000,
        },
      ],
    },
    isLoading: false,
    error: undefined,
    refetch,
  })),
  useCreateAdminDiscountBatchMutation: () => [
    createTrigger,
    { isLoading: false },
  ],
}));

const adminUser: User = {
  id: 'a1',
  email: 'admin@example.com',
  firstName: 'Admin',
  lastName: 'User',
  emailVerified: true,
  role: 'admin',
  createdAt: '',
  updatedAt: '',
};

function renderAdminPage(ui: ReactElement) {
  const store = configureStore({
    reducer: { auth: authReducer },
    preloadedState: {
      auth: {
        user: adminUser,
        token: 'tok',
        refreshToken: 'ref',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    },
  });
  return render(
    <MantineProvider env="test">
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>
    </MantineProvider>
  );
}

describe('AdminDiscountsPage', () => {
  beforeEach(() => {
    createTrigger.mockReset();
    refetch.mockReset();
    createTrigger.mockReturnValue({
      unwrap: vi.fn().mockResolvedValue({
        batchId: 'new-batch',
        count: 10,
        totalAmountCents: 50000,
        currency: 'USD',
        createdAt: '2026-01-02T00:00:00.000Z',
        sampleCodes: [],
      }),
    });
  });

  it('renders batch list with source and generate action', () => {
    renderAdminPage(<AdminDiscountsPage />);
    expect(screen.getByText('G2A_test')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate batch/i })).toBeInTheDocument();
  });

  it('submits create batch with cents and required fields', async () => {
    const user = userEvent.setup();
    renderAdminPage(<AdminDiscountsPage />);
    await user.click(screen.getByRole('button', { name: /generate batch/i }));
    await user.clear(screen.getByLabelText(/number of codes/i));
    await user.type(screen.getByLabelText(/number of codes/i), '5');
    await user.clear(screen.getByLabelText(/face value/i));
    await user.type(screen.getByLabelText(/face value/i), '25');
    await user.clear(screen.getByLabelText(/^source label/i));
    await user.type(screen.getByLabelText(/^source label/i), 'MySource');
    await user.click(screen.getByRole('button', { name: /^create$/i }));

    expect(createTrigger).toHaveBeenCalledWith(
      expect.objectContaining({
        count: 5,
        amountCents: 2500,
        source: 'MySource',
      })
    );
  });
});

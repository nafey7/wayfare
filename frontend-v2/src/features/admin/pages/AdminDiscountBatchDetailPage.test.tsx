import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';

import authReducer from '@/store/slices/authSlice';
import type { User } from '@/types/auth';
import { AdminDiscountBatchDetailPage } from './AdminDiscountBatchDetailPage';

const fetchCsvTrigger = vi.fn();

vi.mock('@/api/adminDiscountsApi', () => ({
  useGetAdminBatchDetailQuery: vi.fn(() => ({
    data: {
      batchId: 'batch-uuid-1',
      source: 'G2A_test',
      createdAt: '2026-01-01T00:00:00.000Z',
      summary: {
        batchId: 'batch-uuid-1',
        total: 1,
        used: 0,
        reserved: 0,
        active: 1,
        expired: 0,
        disabled: 0,
        source: 'G2A_test',
        createdAt: '2026-01-01T00:00:00.000Z',
        totalAmountCents: 5000,
      },
      codes: [
        {
          id: 'test-discount-doc-id',
          code: 'VOYA-ABCD-EFGH',
          amountCents: 5000,
          currency: 'USD',
          status: 'active',
          source: 'G2A_test',
          batchId: 'batch-uuid-1',
          createdAt: '2026-01-01T00:00:00.000Z',
        },
      ],
      totalCodes: 1,
      limit: 50,
      offset: 0,
    },
    isLoading: false,
    error: undefined,
    refetch: vi.fn(),
  })),
  useDisableAdminDiscountMutation: () => [vi.fn(), { isLoading: false }],
  useLazyGetAdminBatchCsvQuery: () => [
    fetchCsvTrigger,
    { isFetching: false },
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

function renderBatchDetail(ui: ReactElement, batchId = 'batch-uuid-1') {
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
        <MemoryRouter initialEntries={[`/admin/discounts/${batchId}`]}>
          <Routes>
            <Route path="/admin/discounts/:batchId" element={ui} />
          </Routes>
        </MemoryRouter>
      </Provider>
    </MantineProvider>
  );
}

describe('AdminDiscountBatchDetailPage', () => {
  beforeEach(() => {
    fetchCsvTrigger.mockReset();
    fetchCsvTrigger.mockReturnValue({
      unwrap: vi.fn().mockResolvedValue(new Blob(['VOYA-AA\n'], { type: 'text/csv' })),
    });
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it('renders code row and summary', () => {
    renderBatchDetail(<AdminDiscountBatchDetailPage />);
    expect(screen.getByText('VOYA-ABCD-EFGH')).toBeInTheDocument();
    expect(screen.getByText(/face value total/i)).toBeInTheDocument();
  });

  it('download CSV triggers lazy query with batch id', async () => {
    const user = userEvent.setup();
    renderBatchDetail(<AdminDiscountBatchDetailPage />);
    await user.click(screen.getByRole('button', { name: /download csv/i }));
    expect(fetchCsvTrigger).toHaveBeenCalledWith('batch-uuid-1');
  });
});

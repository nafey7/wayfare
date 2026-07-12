import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SecuritySection } from './SecuritySection';

const hoisted = vi.hoisted(() => ({
  changePassword: vi.fn(),
  isLoading: false,
}));

vi.mock('@/api/usersApi', () => ({
  useChangePasswordMutation: () => [
    (args: unknown) => ({ unwrap: () => hoisted.changePassword(args) }),
    { isLoading: hoisted.isLoading },
  ],
}));

function renderWithStore(ui: ReactElement) {
  const store = configureStore({ reducer: { _noop: () => null } });
  return render(
    <MemoryRouter>
      <MantineProvider env="test">
        <Provider store={store}>{ui}</Provider>
      </MantineProvider>
    </MemoryRouter>
  );
}

function renderWithRoutes(isAdmin: boolean) {
  const store = configureStore({ reducer: { _noop: () => null } });
  render(
    <MemoryRouter initialEntries={['/profile']}>
      <MantineProvider env="test">
        <Provider store={store}>
          <Routes>
            <Route path="/profile" element={<SecuritySection isAdmin={isAdmin} />} />
            <Route path="/admin/discounts" element={<div>discounts-page</div>} />
            <Route path="/admin/bookings" element={<div>bookings-page</div>} />
          </Routes>
        </Provider>
      </MantineProvider>
    </MemoryRouter>
  );
}

describe('SecuritySection', () => {
  it('renders the Change password button', () => {
    renderWithStore(<SecuritySection />);
    expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument();
  });

  it('shows modal fields on button click', async () => {
    const user = userEvent.setup();
    renderWithStore(<SecuritySection />);
    await user.click(screen.getByRole('button', { name: /change password/i }));
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
  });

  it('shows error when new passwords do not match', async () => {
    const user = userEvent.setup();
    renderWithStore(<SecuritySection />);
    await user.click(screen.getByRole('button', { name: /change password/i }));

    const dialog = screen.getByRole('dialog');
    await user.type(within(dialog).getByLabelText(/current password/i), 'OldPass1!');
    await user.type(within(dialog).getByLabelText(/^new password/i), 'NewPass1!');
    await user.type(within(dialog).getByLabelText(/confirm new password/i), 'Different1!');
    await user.click(within(dialog).getByRole('button', { name: /^change password$/i }));

    expect(await screen.findByText(/new passwords do not match/i)).toBeInTheDocument();
  });

  it('shows error when new password is shorter than 8 characters', async () => {
    const user = userEvent.setup();
    renderWithStore(<SecuritySection />);
    await user.click(screen.getByRole('button', { name: /change password/i }));

    const dialog = screen.getByRole('dialog');
    await user.type(within(dialog).getByLabelText(/current password/i), 'OldPass1!');
    await user.type(within(dialog).getByLabelText(/^new password/i), 'short');
    await user.type(within(dialog).getByLabelText(/confirm new password/i), 'short');
    await user.click(within(dialog).getByRole('button', { name: /^change password$/i }));

    expect(await screen.findByText(/password must be at least 8 characters/i)).toBeInTheDocument();
  });

  it('surfaces API error data.detail on failure', async () => {
    const user = userEvent.setup();
    hoisted.changePassword.mockRejectedValueOnce({
      data: { detail: 'Current password is incorrect' },
    });
    renderWithStore(<SecuritySection />);
    await user.click(screen.getByRole('button', { name: /change password/i }));

    const dialog = screen.getByRole('dialog');
    await user.type(within(dialog).getByLabelText(/current password/i), 'WrongOld!');
    await user.type(within(dialog).getByLabelText(/^new password/i), 'NewPass1!');
    await user.type(within(dialog).getByLabelText(/confirm new password/i), 'NewPass1!');
    await user.click(within(dialog).getByRole('button', { name: /^change password$/i }));

    expect(await screen.findByText(/current password is incorrect/i)).toBeInTheDocument();
  });

  it('does not render Administration heading when isAdmin is false', () => {
    renderWithStore(<SecuritySection />);
    expect(screen.queryByText(/administration/i)).not.toBeInTheDocument();
  });

  it('renders Discounts and Booking Management rows when isAdmin is true', () => {
    renderWithStore(<SecuritySection isAdmin />);
    expect(screen.getByText(/administration/i)).toBeInTheDocument();
    expect(screen.getByText(/discounts/i)).toBeInTheDocument();
    expect(screen.getByText(/booking management/i)).toBeInTheDocument();
  });

  it('navigates to /admin/discounts when Discounts row is clicked', () => {
    renderWithRoutes(true);
    fireEvent.click(screen.getByRole('link', { name: /discounts/i }));
    expect(screen.getByText('discounts-page')).toBeInTheDocument();
  });

  it('navigates to /admin/bookings when Booking Management row is clicked', () => {
    renderWithRoutes(true);
    fireEvent.click(screen.getByRole('link', { name: /booking management/i }));
    expect(screen.getByText('bookings-page')).toBeInTheDocument();
  });

  it('closes modal and clears state on success', async () => {
    const user = userEvent.setup();
    hoisted.changePassword.mockResolvedValueOnce({});
    renderWithStore(<SecuritySection />);
    await user.click(screen.getByRole('button', { name: /change password/i }));

    const dialog = screen.getByRole('dialog');
    await user.type(within(dialog).getByLabelText(/current password/i), 'OldPass1!');
    await user.type(within(dialog).getByLabelText(/^new password/i), 'NewPass99!');
    await user.type(within(dialog).getByLabelText(/confirm new password/i), 'NewPass99!');
    await user.click(within(dialog).getByRole('button', { name: /^change password$/i }));

    await waitFor(() => {
      expect(screen.queryByLabelText(/current password/i)).not.toBeInTheDocument();
    });
  });
});

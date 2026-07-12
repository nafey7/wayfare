import type { ReactElement } from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { configureStore, createSlice } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { AvatarUpload } from './AvatarUpload';

const hoisted = vi.hoisted(() => ({
  uploadFn: vi.fn(),
  deleteFn: vi.fn(),
  uploading: false,
  deleting: false,
}));

vi.mock('@/api/usersApi', () => ({
  useUploadProfilePhotoMutation: () => [
    (file: File) => ({ unwrap: () => hoisted.uploadFn(file) }),
    { isLoading: hoisted.uploading },
  ],
  useDeleteProfilePhotoMutation: () => [
    () => ({ unwrap: () => hoisted.deleteFn() }),
    { isLoading: hoisted.deleting },
  ],
}));

function makeStore() {
  const authSlice = createSlice({
    name: 'auth',
    initialState: { user: { id: 'u1', email: 'u@x.com' } },
    reducers: {
      setUserPhoto: (state, action) => {
        if (state.user) Object.assign(state.user, action.payload);
      },
    },
  });
  return configureStore({ reducer: { auth: authSlice.reducer } });
}

function renderWithProviders(ui: ReactElement) {
  return render(
    <MantineProvider env="test">
      <Provider store={makeStore()}>{ui}</Provider>
    </MantineProvider>
  );
}

beforeEach(() => {
  hoisted.uploadFn.mockReset();
  hoisted.deleteFn.mockReset();
  hoisted.uploading = false;
  hoisted.deleting = false;
});

describe('AvatarUpload', () => {
  it('renders an upload button when there is no photo', () => {
    renderWithProviders(
      <AvatarUpload photoUrls={null} displayName="Jane Smith" />
    );
    expect(
      screen.getByRole('button', { name: /upload profile photo/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /remove profile photo/i })
    ).not.toBeInTheDocument();
  });

  it('renders Change and Remove when a photo exists', () => {
    renderWithProviders(
      <AvatarUpload
        photoUrls={{ sm: '/sm', md: '/md', lg: '/lg' }}
        displayName="Jane"
      />
    );
    expect(
      screen.getByRole('button', { name: /change profile photo/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /remove profile photo/i })
    ).toBeInTheDocument();
  });

  it('rejects oversize files without calling the API', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AvatarUpload photoUrls={null} displayName="Jane" />
    );
    const big = new File([new Uint8Array(6 * 1024 * 1024)], 'big.jpg', {
      type: 'image/jpeg',
    });
    const input = screen.getByTestId('avatar-upload-input') as HTMLInputElement;
    await user.upload(input, big);
    expect(hoisted.uploadFn).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent(/5 MB/i);
  });

  it('rejects unsupported mime types', async () => {
    renderWithProviders(
      <AvatarUpload photoUrls={null} displayName="Jane" />
    );
    const gif = new File([new Uint8Array(100)], 'x.gif', { type: 'image/gif' });
    const input = screen.getByTestId('avatar-upload-input') as HTMLInputElement;
    // Bypass user-event's accept-attribute filtering by firing the change directly.
    Object.defineProperty(input, 'files', { value: [gif], configurable: true });
    fireEvent.change(input);
    expect(hoisted.uploadFn).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/JPEG, PNG, or WebP image/i)
    ).toBeInTheDocument();
  });

  it('calls the upload mutation for a valid file', async () => {
    hoisted.uploadFn.mockResolvedValueOnce({
      photoKey: 'users/u1/avatar/abc.jpg',
      photoUrls: { sm: '/sm', md: '/md', lg: '/lg' },
    });
    const user = userEvent.setup();
    renderWithProviders(
      <AvatarUpload photoUrls={null} displayName="Jane" />
    );
    const ok = new File([new Uint8Array(100)], 'avatar.jpg', {
      type: 'image/jpeg',
    });
    const input = screen.getByTestId('avatar-upload-input') as HTMLInputElement;
    await user.upload(input, ok);
    await waitFor(() => expect(hoisted.uploadFn).toHaveBeenCalledTimes(1));
  });

  it('confirms before deleting via Mantine modal', async () => {
    const user = userEvent.setup();
    hoisted.deleteFn.mockResolvedValueOnce(undefined);
    renderWithProviders(
      <AvatarUpload
        photoUrls={{ sm: '/sm', md: '/md', lg: '/lg' }}
        displayName="Jane"
      />
    );
    await user.click(
      screen.getByRole('button', { name: /remove profile photo/i })
    );
    // Modal opens with a destructive confirm button labelled "Remove".
    const confirmButton = await screen.findByRole('button', { name: /^remove$/i });
    await user.click(confirmButton);
    await waitFor(() => expect(hoisted.deleteFn).toHaveBeenCalled());
  });
});

import { useEffect, useRef, useState } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setTokens, setUser } from '@/store/slices/authSlice';
import type { User } from '@/types/auth';

type ExchangeTokenMutation = (args: { authToken: string }) => {
  unwrap: () => Promise<{ accessToken: string; refreshToken: string }>;
};
type GetMeLazy = () => { unwrap: () => Promise<User> };

interface UseEmailLinkAuthOptions {
  isEmailLinkMode: boolean;
  authTokenFromUrl: string | null;
  exchangeToken: ExchangeTokenMutation;
  getMe: GetMeLazy;
}

interface UseEmailLinkAuthResult {
  authDone: boolean;
  wrongAccount: boolean;
}

/**
 * Shared hook for email-link auth: exchange auth_token for JWT, set tokens + user, handle 403 (wrong account).
 * Used by FlightBookingDetailsPage, PaymentPage (flights), and HotelPaymentPage.
 */
export function useEmailLinkAuth({
  isEmailLinkMode,
  authTokenFromUrl,
  exchangeToken,
  getMe,
}: UseEmailLinkAuthOptions): UseEmailLinkAuthResult {
  const dispatch = useAppDispatch();
  const exchangedRef = useRef(false);
  const [authDone, setAuthDone] = useState(false);
  const [wrongAccount, setWrongAccount] = useState(false);

  useEffect(() => {
    if (!isEmailLinkMode || !authTokenFromUrl || exchangedRef.current) return;
    exchangedRef.current = true;
    setWrongAccount(false);
    exchangeToken({ authToken: authTokenFromUrl })
      .unwrap()
      .then((res) => {
        dispatch(setTokens({ accessToken: res.accessToken, refreshToken: res.refreshToken }));
        return getMe().unwrap();
      })
      .then((user) => {
        dispatch(setUser(user));
        setAuthDone(true);
      })
      .catch((err: { status?: number }) => {
        if (err?.status === 403) setWrongAccount(true);
        setAuthDone(true);
      });
  }, [isEmailLinkMode, authTokenFromUrl, exchangeToken, getMe, dispatch]);

  useEffect(() => {
    if (isEmailLinkMode && !authTokenFromUrl) setAuthDone(true);
  }, [isEmailLinkMode, authTokenFromUrl]);

  return { authDone, wrongAccount };
}

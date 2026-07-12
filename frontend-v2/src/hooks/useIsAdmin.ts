import { useAppSelector } from '@/store';
import { selectCurrentUser } from '@/store/slices/authSlice';

/** True when the signed-in user may access admin-only UI (matches AdminBookingsPage). */
export function useIsAdmin(): boolean {
  const user = useAppSelector(selectCurrentUser);
  return user?.role === 'admin' || user?.role === 'super_admin';
}

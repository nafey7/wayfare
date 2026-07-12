import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '@/store';
import { clearUserSession } from '@/store/thunks/clearUserSession';

export function useSignOut() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  return () => {
    dispatch(clearUserSession());
    navigate('/');
  };
}

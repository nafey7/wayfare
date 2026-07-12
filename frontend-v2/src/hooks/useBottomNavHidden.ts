import { useAppSelector } from '@/store';
import { selectBottomNavHidden } from '@/store/slices/uiSlice';
import { useScrollDirectionHidden } from './useScrollDirectionHidden';

export function useBottomNavHidden(): boolean {
  const scrollHidden = useScrollDirectionHidden();
  const flagHidden = useAppSelector(selectBottomNavHidden);
  return scrollHidden || flagHidden;
}

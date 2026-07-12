import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useScrollDirectionHidden } from './useScrollDirectionHidden';

function setScrollY(value: number) {
  Object.defineProperty(window, 'scrollY', { value, writable: true, configurable: true });
}

async function fireScroll(scrollY: number) {
  setScrollY(scrollY);
  window.dispatchEvent(new Event('scroll'));
  // Flush the requestAnimationFrame callback used for rAF throttling
  await act(async () => {
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  });
}

describe('useScrollDirectionHidden', () => {
  beforeEach(() => {
    setScrollY(0);
  });

  it('returns false initially', () => {
    const { result } = renderHook(() => useScrollDirectionHidden());
    expect(result.current).toBe(false);
  });

  it('returns true when scrolling down past 60px', async () => {
    const { result } = renderHook(() => useScrollDirectionHidden());

    await fireScroll(100);

    expect(result.current).toBe(true);
  });

  it('does not hide when scrolling down but below 60px threshold', async () => {
    const { result } = renderHook(() => useScrollDirectionHidden());

    await fireScroll(40);

    expect(result.current).toBe(false);
  });

  it('returns false again when scrolling back up', async () => {
    const { result } = renderHook(() => useScrollDirectionHidden());

    await fireScroll(100);
    expect(result.current).toBe(true);

    await fireScroll(50);
    expect(result.current).toBe(false);
  });

  it('stays hidden when scrolling further down', async () => {
    const { result } = renderHook(() => useScrollDirectionHidden());

    await fireScroll(100);
    expect(result.current).toBe(true);

    await fireScroll(200);
    expect(result.current).toBe(true);
  });
});

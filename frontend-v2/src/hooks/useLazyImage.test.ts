import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useLazyImage, isPlaceholderInView } from './useLazyImage';

function mockInViewRect(el: HTMLElement): void {
  vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({
    width: 80,
    height: 80,
    top: 100,
    left: 100,
    bottom: 180,
    right: 180,
    x: 100,
    y: 100,
    toJSON: () => ({}),
  } as DOMRect);
}

describe('useLazyImage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, 'innerWidth', { value: 1024, configurable: true });
    Object.defineProperty(window, 'innerHeight', { value: 768, configurable: true });
  });

  it('when disabled, isVisible is true without waiting', () => {
    const { result } = renderHook(() => useLazyImage({ disabled: true }));
    expect(result.current.isVisible).toBe(true);
  });

  it('when not disabled, becomes visible when manual check passes', async () => {
    const { result } = renderHook(() => useLazyImage({ disabled: false, rootMargin: '150px' }));

    expect(result.current.isVisible).toBe(false);

    const div = document.createElement('div');
    document.body.appendChild(div);
    mockInViewRect(div);

    await act(async () => {
      result.current.ref(div);
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
    });

    expect(result.current.isVisible).toBe(true);
    document.body.removeChild(div);
  });
});

describe('isPlaceholderInView', () => {
  it('returns false for zero-size rect', () => {
    const el = document.createElement('div');
    vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({
      width: 0,
      height: 0,
      top: 0,
      left: 0,
      bottom: 0,
      right: 0,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect);
    expect(isPlaceholderInView(el, 0)).toBe(false);
  });
});

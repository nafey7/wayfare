import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useBottomSheet, type BottomSheetSnapHeights } from './useBottomSheet';

const SNAPS: BottomSheetSnapHeights = { minimized: 44, half: 380, full: 'full' };

// Silence act() warnings from useEffect inside renderHook.
beforeEach(() => {
  vi.restoreAllMocks();
});

describe('useBottomSheet — sheetStyle', () => {
  it('sets height to minimized px when snap is minimized', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'minimized', snaps: SNAPS })
    );
    expect(result.current.sheetStyle.height).toBe(44);
  });

  it('sets height to half px when snap is half', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'half', snaps: SNAPS })
    );
    expect(result.current.sheetStyle.height).toBe(380);
  });

  it('sets height to calc CSS string when snap is full', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'full', snaps: SNAPS, bottomOffset: 48, topReserve: 0 })
    );
    expect(typeof result.current.sheetStyle.height).toBe('string');
    expect(result.current.sheetStyle.height).toMatch(/calc/);
  });

  it('applies custom zIndex', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'minimized', snaps: SNAPS, zIndex: 9999 })
    );
    expect(result.current.sheetStyle.zIndex).toBe(9999);
  });

  it('is positioned absolute at bottom 0 by default', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'half', snaps: SNAPS })
    );
    expect(result.current.sheetStyle.position).toBe('absolute');
    expect(result.current.sheetStyle.left).toBe(0);
    expect(result.current.sheetStyle.right).toBe(0);
    expect(result.current.sheetStyle.bottom).toBe(0);
  });
});

describe('useBottomSheet — handleProps', () => {
  it('returns onClick and touch handlers', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'half', snaps: SNAPS })
    );
    const { handleProps } = result.current;
    expect(typeof handleProps.onClick).toBe('function');
    expect(typeof handleProps.onTouchStart).toBe('function');
    expect(typeof handleProps.onTouchEnd).toBe('function');
  });

  it('returns touchAction: none to prevent default scroll on handle', () => {
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'half', snaps: SNAPS })
    );
    expect(result.current.handleProps.style.touchAction).toBe('none');
  });
});

describe('useBottomSheet — tap-to-cycle via handleProps.onClick', () => {
  const mockClick = (target = document.createElement('span')) =>
    ({ target } as unknown as Parameters<ReturnType<typeof useBottomSheet>['handleProps']['onClick']>[0]);

  it('advances minimized → half on tap', () => {
    const onSnapChange = vi.fn();
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'minimized', snaps: SNAPS, onSnapChange })
    );
    result.current.handleProps.onClick(mockClick());
    expect(onSnapChange).toHaveBeenCalledWith('half');
  });

  it('advances half → full on tap', () => {
    const onSnapChange = vi.fn();
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'half', snaps: SNAPS, onSnapChange })
    );
    result.current.handleProps.onClick(mockClick());
    expect(onSnapChange).toHaveBeenCalledWith('full');
  });

  it('advances full → half on tap', () => {
    const onSnapChange = vi.fn();
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'full', snaps: SNAPS, onSnapChange })
    );
    result.current.handleProps.onClick(mockClick());
    expect(onSnapChange).toHaveBeenCalledWith('half');
  });

  it('does not call onSnapChange when clicking a button inside the handle', () => {
    const onSnapChange = vi.fn();
    const { result } = renderHook(() =>
      useBottomSheet({ snap: 'half', snaps: SNAPS, onSnapChange })
    );
    const btn = document.createElement('button');
    result.current.handleProps.onClick(mockClick(btn));
    expect(onSnapChange).not.toHaveBeenCalled();
  });
});

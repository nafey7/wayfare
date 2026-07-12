import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useScrollCollapsed } from './useScrollCollapsed';

function setScrollY(value: number) {
  Object.defineProperty(window, 'scrollY', { value, writable: true, configurable: true });
}

async function fireScroll(scrollY: number) {
  setScrollY(scrollY);
  window.dispatchEvent(new Event('scroll'));
  await act(async () => {
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  });
}

// Thresholds used throughout: collapseAt=100, expandAt=50
// Dead zone: scrollY in [50, 100] — collapsed stays collapsed, uncollapsed stays uncollapsed
describe('useScrollCollapsed', () => {
  beforeEach(() => {
    setScrollY(0);
  });

  it('(a) starts uncollapsed when scrollY is 0 (below collapseAt)', () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));
    expect(result.current).toBe(false);
  });

  it('(a) starts uncollapsed when initial scrollY is inside the dead zone', async () => {
    setScrollY(70);
    const { result } = renderHook(() => useScrollCollapsed(100, 50));
    // Flush the rAF triggered by handler() on mount
    await act(async () => {
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    });
    expect(result.current).toBe(false);
  });

  it('(b) stays uncollapsed while scrollY is below collapseAt', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    await fireScroll(99);

    expect(result.current).toBe(false);
  });

  it('(b) collapses only after scrollY strictly exceeds collapseAt', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    // Exactly at the threshold — should NOT collapse (condition is y > collapseAt)
    await fireScroll(100);
    expect(result.current).toBe(false);

    // One pixel over — should collapse
    await fireScroll(101);
    expect(result.current).toBe(true);
  });

  it('(c) stays collapsed when scrollY is in the dead zone [expandAt, collapseAt]', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    await fireScroll(110);
    expect(result.current).toBe(true);

    // Multiple positions inside the dead zone
    await fireScroll(99);
    expect(result.current).toBe(true);

    await fireScroll(70);
    expect(result.current).toBe(true);

    await fireScroll(50);
    expect(result.current).toBe(true);
  });

  it('(d) un-collapses only when scrollY drops strictly below expandAt', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    await fireScroll(110);
    expect(result.current).toBe(true);

    // Dead zone: still collapsed
    await fireScroll(60);
    expect(result.current).toBe(true);

    // Exactly at expandAt — condition is y < expandAt, so no change
    await fireScroll(50);
    expect(result.current).toBe(true);

    // Below expandAt: un-collapses
    await fireScroll(49);
    expect(result.current).toBe(false);
  });

  it('can collapse and expand multiple times', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    await fireScroll(110);
    expect(result.current).toBe(true);

    await fireScroll(30);
    expect(result.current).toBe(false);

    await fireScroll(120);
    expect(result.current).toBe(true);

    await fireScroll(10);
    expect(result.current).toBe(false);
  });
});

// These tests mount an actual <div id="main-scroll-root"> so the hook binds to
// the element (scrollTop) instead of falling back to window (scrollY). This
// locks down the integration with the landing-page refactor that introduced
// the scroll container.
describe('useScrollCollapsed — main-scroll-root element path', () => {
  let scrollRoot: HTMLDivElement;

  beforeEach(() => {
    setScrollY(0);
    scrollRoot = document.createElement('div');
    scrollRoot.id = 'main-scroll-root';
    Object.defineProperty(scrollRoot, 'scrollTop', { value: 0, writable: true, configurable: true });
    document.body.appendChild(scrollRoot);
  });

  afterEach(() => {
    scrollRoot.remove();
  });

  async function fireScrollOnRoot(scrollTop: number) {
    Object.defineProperty(scrollRoot, 'scrollTop', { value: scrollTop, writable: true, configurable: true });
    scrollRoot.dispatchEvent(new Event('scroll'));
    await act(async () => {
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    });
  }

  it('collapses when element scrollTop exceeds collapseAt', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    await fireScrollOnRoot(101);

    expect(result.current).toBe(true);
  });

  it('does not collapse when window.scrollY is high but element scrollTop is low', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    // Hook is bound to the element — a window scroll event should be ignored
    setScrollY(200);
    window.dispatchEvent(new Event('scroll'));
    await act(async () => {
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    });

    expect(result.current).toBe(false);
  });

  it('respects the dead zone and expands when element scrollTop drops below expandAt', async () => {
    const { result } = renderHook(() => useScrollCollapsed(100, 50));

    await fireScrollOnRoot(110);
    expect(result.current).toBe(true);

    await fireScrollOnRoot(70); // inside dead zone — stays collapsed
    expect(result.current).toBe(true);

    await fireScrollOnRoot(49); // below expandAt — expands
    expect(result.current).toBe(false);
  });
});

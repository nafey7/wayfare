import { useEffect, useRef, type CSSProperties, type MouseEvent, type RefObject, type TouchEvent } from 'react';

/**
 * Generic snap states for a bottom sheet, low → high.
 * Consumers map their semantic state names to these:
 *   - ChatSheet: 'resting' | 'half' | 'full' → 'minimized' | 'half' | 'full'
 */
export type BottomSheetSnap = 'minimized' | 'half' | 'full';

export interface BottomSheetSnapHeights {
  /** Pixel height when at the "low" snap. */
  minimized: number;
  /** Pixel height when at the "mid" snap. */
  half: number;
  /** 'full' is computed at runtime as `parent.clientHeight - bottomOffset`. */
  full: 'full';
}

export interface UseBottomSheetOptions {
  snap: BottomSheetSnap;
  snaps: BottomSheetSnapHeights;
  onSnapChange?: (snap: BottomSheetSnap) => void;
  /** Reserved chrome below the sheet (BottomNav + ChatComposerBar). Number (px) or CSS string. */
  bottomOffset?: number | string;
  /** Pixels reserved at the top of the parent that the sheet should NOT cover at full snap.
   *  Used to cap the sheet's full-snap height (e.g. so a chat sheet stops at the bottom of the
   *  unified header's subtabs row instead of overlapping the header). */
  topReserve?: number;
  /** Stacking order. Defaults to 14 for back-compat with existing HotelBottomSheet. */
  zIndex?: number;
  /** Tap-to-cycle order from the handle. Defaults to: minimized→half, half→full, full→half. */
  tapCycle?: Record<BottomSheetSnap, BottomSheetSnap>;
}

export interface UseBottomSheetResult {
  /** Attach to the outer sheet container. */
  sheetRef: RefObject<HTMLDivElement>;
  /** Spread onto the outer sheet container's `style` (or merge into sx). */
  sheetStyle: CSSProperties;
  /** Attach to the header / drag-handle element (non-passive touchmove is registered here). */
  handleRef: RefObject<HTMLDivElement>;
  /** Spread onto the header element. */
  handleProps: {
    onClick: (e: MouseEvent) => void;
    onTouchStart: (e: TouchEvent) => void;
    onTouchEnd: (e: TouchEvent) => void;
    style: CSSProperties;
  };
  /** Attach to the scrollable list / body. Drag-to-resize is auto-attached when snap !== 'full'. */
  listRef: RefObject<HTMLDivElement>;
}

const DEFAULT_TAP_CYCLE: Record<BottomSheetSnap, BottomSheetSnap> = {
  minimized: 'half',
  half: 'full',
  full: 'half',
};

function getFullH(sheet: HTMLElement, topReserve = 0): number {
  // Parent height minus the sheet's own bottom offset — so "full" means filling
  // up to the bottom-reserved chrome (BottomNav + ChatComposerBar), not the
  // entire parent. Without this, the sheet at full snap would overflow above
  // the parent by `bottomOffset` pixels. `topReserve` further caps the height
  // so the sheet stops below a reserved top region (e.g. unified header).
  const parentH = sheet.parentElement?.clientHeight ?? window.innerHeight;
  const bottomPx = parseFloat(getComputedStyle(sheet).bottom) || 0;
  return Math.max(0, parentH - bottomPx - topReserve);
}

function snapPx(s: BottomSheetSnap, snaps: BottomSheetSnapHeights, sheet: HTMLElement, topReserve: number): number {
  return s === 'full' ? getFullH(sheet, topReserve) : snaps[s];
}

function nearestSnap(h: number, snaps: BottomSheetSnapHeights, sheet: HTMLElement, topReserve: number): BottomSheetSnap {
  const candidates: [BottomSheetSnap, number][] = [
    ['minimized', snaps.minimized],
    ['half',      snaps.half],
    ['full',      getFullH(sheet, topReserve)],
  ];
  return candidates.reduce(
    (best, [s, px]) => (Math.abs(px - h) < Math.abs(snapPx(best, snaps, sheet, topReserve) - h) ? s : best),
    'half' as BottomSheetSnap
  );
}

/**
 * Snap-sheet behavior — drag/velocity gestures, snap math, sheet positioning.
 *
 * Returns refs + style + event handlers to attach to your own JSX. The hook
 * intentionally does NOT render — consumers own their visuals (handle bar look,
 * header content, list, optional footer overlays).
 */
export function useBottomSheet({
  snap,
  snaps,
  onSnapChange,
  bottomOffset = 0,
  topReserve = 0,
  zIndex = 14,
  tapCycle = DEFAULT_TAP_CYCLE,
}: UseBottomSheetOptions): UseBottomSheetResult {
  const sheetRef  = useRef<HTMLDivElement>(null);
  const handleRef = useRef<HTMLDivElement>(null);
  const listRef   = useRef<HTMLDivElement>(null);

  // drag state — kept in a ref so updates don't cause re-renders.
  // mode is decided on the first significant touchmove and locked for the gesture.
  const drag = useRef<{
    startY: number;
    startX: number;
    startH: number;
    startTime: number;
    moved: boolean;
    mode: 'idle' | 'dragging' | 'scrolling';
  } | null>(null);

  // Prevent the click handler from firing after a real drag.
  const suppressClick = useRef(false);

  // Non-passive touchmove on the header bar — drag to resize.
  // Depends on `snap` so it re-runs when consumers (e.g. ChatSheet) conditionally
  // render the handle element based on snap state — without this, the listener
  // never attaches if the handle wasn't in the DOM on initial mount.
  useEffect(() => {
    const handle = handleRef.current;
    if (!handle) return;

    const onMove = (e: globalThis.TouchEvent) => {
      if (!drag.current || !sheetRef.current) return;
      e.preventDefault();

      const dy = drag.current.startY - e.touches[0]!.clientY;
      if (Math.abs(dy) > 4) drag.current.moved = true;
      drag.current.mode = 'dragging';

      const max = getFullH(sheetRef.current, topReserve);
      const newH = Math.max(snaps.minimized, Math.min(max, drag.current.startH + dy));
      sheetRef.current.style.height = `${newH}px`;
    };

    handle.addEventListener('touchmove', onMove, { passive: false });
    return () => handle.removeEventListener('touchmove', onMove);
    // `topReserve` intentionally excluded — re-binding the touch listener mid-drag
    // when the reserve changes would interrupt user interaction. Stale value is fine
    // here; max is recomputed inside `onMove` from the live ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap, snaps.minimized]);

  // When sheet is NOT full, treat any drag inside the list area as sheet-resize too.
  // (At full snap we DON'T attach this listener, so list scrolls 100% natively.)
  useEffect(() => {
    if (snap === 'full') return;
    const list = listRef.current;
    if (!list) return;

    const onStart = (e: globalThis.TouchEvent) => {
      if (!sheetRef.current) return;
      drag.current = {
        startY: e.touches[0]!.clientY,
        startX: e.touches[0]!.clientX,
        startH: sheetRef.current.getBoundingClientRect().height,
        startTime: Date.now(),
        moved: false,
        mode: 'idle',
      };
      sheetRef.current.style.transition = 'none';
    };

    const onMove = (e: globalThis.TouchEvent) => {
      if (!drag.current || !sheetRef.current) return;
      const list = listRef.current;

      // Once mode is decided, stay in it for the rest of this gesture.
      if (drag.current.mode === 'scrolling') return;

      // If the list has been scrolled down, let native scroll handle it.
      if (list && list.scrollTop > 0) {
        drag.current.mode = 'scrolling';
        return;
      }

      const dy = drag.current.startY - e.touches[0]!.clientY;
      const dx = drag.current.startX - e.touches[0]!.clientX;

      // Horizontal swipe (photo carousel etc.) — let child handle it, don't resize sheet.
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 6) {
        drag.current.mode = 'scrolling';
        return;
      }

      // At scroll top with a vertical gesture — intercept and resize the sheet.
      e.preventDefault();
      if (Math.abs(dy) > 4) drag.current.moved = true;
      drag.current.mode = 'dragging';
      const max = getFullH(sheetRef.current, topReserve);
      const newH = Math.max(snaps.minimized, Math.min(max, drag.current.startH + dy));
      sheetRef.current.style.height = `${newH}px`;
    };

    const onEnd = (e: globalThis.TouchEvent) => {
      if (!drag.current || !sheetRef.current) return;
      const { startY, startH, startTime, moved, mode } = drag.current;
      drag.current = null;
      sheetRef.current.style.transition = '';
      if (mode !== 'dragging') return;
      if (!moved) {
        sheetRef.current.style.height = '';
        return;
      }
      suppressClick.current = true;
      const deltaY  = startY - e.changedTouches[0]!.clientY;
      const elapsed = Date.now() - startTime;
      const velocity = deltaY / elapsed;
      sheetRef.current.style.height = '';
      let next: BottomSheetSnap;
      // snap is narrowed to 'half' | 'minimized' here (effect early-returns on 'full')
      if (velocity > 0.4) next = snap === 'minimized' ? 'half' : 'full';
      else if (velocity < -0.4) next = 'minimized';
      else next = nearestSnap(startH + deltaY, snaps, sheetRef.current, topReserve);
      onSnapChange?.(next);
    };

    list.addEventListener('touchstart', onStart, { passive: false });
    list.addEventListener('touchmove', onMove, { passive: false });
    list.addEventListener('touchend', onEnd);
    return () => {
      list.removeEventListener('touchstart', onStart);
      list.removeEventListener('touchmove', onMove);
      list.removeEventListener('touchend', onEnd);
    };
    // Same reason as the touchmove effect above — `topReserve` is read live via
    // closure inside the handlers; rebinding on every reserve change would
    // interrupt active drags.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap, snaps, onSnapChange]);

  const onDragStart = (e: TouchEvent) => {
    if (!sheetRef.current) return;
    drag.current = {
      startY:    e.touches[0]!.clientY,
      startX:    e.touches[0]!.clientX,
      startH:    sheetRef.current.getBoundingClientRect().height,
      startTime: Date.now(),
      moved:     false,
      mode:      'idle',
    };
    sheetRef.current.style.transition = 'none';
  };

  const onDragEnd = (e: TouchEvent) => {
    if (!drag.current || !sheetRef.current) return;
    const { startY, startH, startTime, moved, mode } = drag.current;
    drag.current = null;

    sheetRef.current.style.transition = '';

    // Pure tap — onMove never ran, so style.height was never inlined. Leaving
    // React's inline height intact lets the click event synthesize on the
    // intended target.
    if (mode !== 'dragging') return;

    // Drag engaged but didn't cross the move threshold — clear the inline height.
    if (!moved) {
      sheetRef.current.style.height = '';
      return;
    }

    suppressClick.current = true;

    const deltaY   = startY - e.changedTouches[0]!.clientY;
    const elapsed  = Date.now() - startTime;
    const velocity = deltaY / elapsed;

    sheetRef.current.style.height = '';

    let next: BottomSheetSnap;
    if (velocity > 0.4) {
      next = snap === 'minimized' ? 'half' : 'full';
    } else if (velocity < -0.4) {
      next = snap === 'full' ? 'half' : 'minimized';
    } else {
      next = nearestSnap(startH + deltaY, snaps, sheetRef.current, topReserve);
    }

    onSnapChange?.(next);
  };

  const onHandleTap = (e: MouseEvent) => {
    // Ignore clicks on interactive elements (buttons inside the header).
    if ((e.target as Element).closest?.('button')) return;
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    onSnapChange?.(tapCycle[snap]);
  };

  const bottomOffsetCss = typeof bottomOffset === 'number' ? `${bottomOffset}px` : bottomOffset;

  const sheetStyle: CSSProperties = {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: bottomOffset,
    height: snap === 'full' ? `calc(100% - ${bottomOffsetCss} - ${topReserve}px)` : snaps[snap],
    zIndex,
    transition: 'height 280ms cubic-bezier(0.32, 0.72, 0, 1), bottom 240ms cubic-bezier(0.32, 0.72, 0, 1)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  };

  const handleProps = {
    onClick: onHandleTap,
    onTouchStart: onDragStart,
    onTouchEnd: onDragEnd,
    style: {
      flexShrink: 0,
      userSelect: 'none' as const,
      cursor: 'row-resize' as const,
      touchAction: 'none' as const,
    },
  };

  return { sheetRef, sheetStyle, handleRef, handleProps, listRef };
}

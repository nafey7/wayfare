import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';

const mockScrollTo = vi.fn();
const mockPathname = vi.fn(() => '/');

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname() }),
}));

import { ScrollToTop } from './ScrollToTop';

describe('ScrollToTop', () => {
  beforeEach(() => {
    mockScrollTo.mockClear();
    vi.stubGlobal('scrollTo', mockScrollTo);
    mockPathname.mockReturnValue('/');
  });

  it('scrolls to top on mount', () => {
    render(<ScrollToTop />);
    expect(mockScrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'instant' });
  });

  it('scrolls again when pathname changes', () => {
    const { rerender } = render(<ScrollToTop />);
    expect(mockScrollTo).toHaveBeenCalledTimes(1);

    mockPathname.mockReturnValue('/flights/search');
    rerender(<ScrollToTop />);
    expect(mockScrollTo).toHaveBeenCalledTimes(2);
  });

  it('scrolls on back navigation (POP)', () => {
    const { rerender } = render(<ScrollToTop />);
    expect(mockScrollTo).toHaveBeenCalledTimes(1);

    mockPathname.mockReturnValue('/');
    rerender(<ScrollToTop />);
    // pathname didn't change, so no extra scroll
    expect(mockScrollTo).toHaveBeenCalledTimes(1);

    mockPathname.mockReturnValue('/flights/search');
    rerender(<ScrollToTop />);
    expect(mockScrollTo).toHaveBeenCalledTimes(2);
  });
});

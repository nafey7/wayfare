import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { searchCitiesOpenMeteo } from '@/features/onboarding/openMeteoGeocoding';
import type { CitySearchOption } from '@/features/onboarding/openMeteoGeocoding';
import { CitySearchAutocomplete } from './CitySearchAutocomplete';

vi.mock('@/features/onboarding/openMeteoGeocoding');
vi.mock('@/hooks/useDebounce', () => ({
  useDebounce: (value: unknown) => value,
}));

const mockSearch = vi.mocked(searchCitiesOpenMeteo);

// Two options that share a display label but have distinct internal values —
// the exact scenario that caused silent selection drops before the fix at line 106.
const SPRINGFIELD_IL: CitySearchOption = {
  value: 'om-111',
  label: 'Springfield, US',
  displayLine: 'Springfield · US',
  countryCode: 'US',
};
const SPRINGFIELD_MA: CitySearchOption = {
  value: 'om-222',
  label: 'Springfield, US',
  displayLine: 'Springfield · US',
  countryCode: 'US',
};

function setup() {
  const onChange = vi.fn();
  const user = userEvent.setup();
  render(<CitySearchAutocomplete label="City" value={null} onChange={onChange} />);
  return { onChange, user, input: screen.getByRole('textbox') };
}

describe('CitySearchAutocomplete', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('calls onChange with the correct option when option value differs from its label', async () => {
    mockSearch.mockResolvedValue([SPRINGFIELD_IL]);
    const { onChange, user, input } = setup();

    await user.type(input, 'Spring');

    const option = await screen.findByRole('option');
    await user.click(option);

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith(SPRINGFIELD_IL);
  });

  it('calls onChange with the correct option when two options share a label but have distinct values', async () => {
    mockSearch.mockResolvedValue([SPRINGFIELD_IL, SPRINGFIELD_MA]);
    const { onChange, user, input } = setup();

    await user.type(input, 'Spring');

    const options = await screen.findAllByRole('option');
    expect(options).toHaveLength(2);

    // Select the second option — old code would have returned SPRINGFIELD_IL
    // (first label match) instead of SPRINGFIELD_MA (correct value match).
    await user.click(options[1]!);

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith(SPRINGFIELD_MA);
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { CountrySelect } from './CountrySelect';
import { countries } from '@/data';

function Wrapper({ children }: { children: React.ReactNode }) {
  return <MantineProvider env="test">{children}</MantineProvider>;
}

describe('CountrySelect — regression: #975', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  // Mantine Select rejects duplicate option `value`s. Multiple countries share
  // dial codes (+1 US/CA, +44 UK/crown deps, +61 AU/CC/CX, …), so the original
  // `variant='phone'` mapping (option-value = `c.phone`) crashed and rendered
  // a blank screen on `/flights/passenger-info` and `/hotels/review-booking`.
  // CountrySelect now keys options by ISO code (unique) and translates at the
  // boundary — these tests assert that no Mantine duplicate-option error fires.
  function getDupErrors(spy: ReturnType<typeof vi.spyOn>) {
    return spy.mock.calls.flat().filter((arg: unknown) => {
      const s = typeof arg === 'string' ? arg : arg instanceof Error ? arg.message : '';
      return s.includes('Duplicate options are not supported');
    });
  }

  it('phone variant renders without duplicate-option error', () => {
    render(
      <Wrapper>
        <CountrySelect value="" onChange={() => {}} variant="phone" />
      </Wrapper>
    );
    expect(getDupErrors(consoleErrorSpy)).toHaveLength(0);
  });

  it('country variant renders without duplicate-option error', () => {
    render(
      <Wrapper>
        <CountrySelect value="" onChange={() => {}} variant="country" />
      </Wrapper>
    );
    expect(getDupErrors(consoleErrorSpy)).toHaveLength(0);
  });

  it('phone variant renders with prefilled shared dial code (+61)', () => {
    // "61" is shared by AU, CC, CX. Confirm the inbound prefill still mounts.
    render(
      <Wrapper>
        <CountrySelect value="61" onChange={() => {}} variant="phone" />
      </Wrapper>
    );
    expect(getDupErrors(consoleErrorSpy)).toHaveLength(0);
  });

  it('phone variant: onChange emits the dial code (not the ISO code)', async () => {
    // Coverage gap flagged by auto-review on PR #977: the regression tests above
    // assert no crash, but don't verify the ISO-code → dial-code translation in
    // handleChange. A future refactor that drops the translation would still
    // pass the no-crash tests; this test guards the API contract.
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <Wrapper>
        <CountrySelect value="" onChange={onChange} variant="phone" label="Phone country" />
      </Wrapper>
    );
    const combobox = screen.getByRole('textbox', { name: 'Phone country' });
    await user.click(combobox);
    // Search for Australia by typing — Mantine filters options
    await user.type(combobox, 'AU');
    const auOption = await screen.findByRole('option', { name: /^AU \+61$/ });
    await user.click(auOption);
    // The emitted value must be the dial code "61", not the ISO code "AU"
    expect(onChange).toHaveBeenCalledWith('61');
  });

  it('country variant: onChange emits the ISO code', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <Wrapper>
        <CountrySelect value="" onChange={onChange} variant="country" label="Country" />
      </Wrapper>
    );
    const combobox = screen.getByRole('textbox', { name: 'Country' });
    await user.click(combobox);
    await user.type(combobox, 'United States');
    const usOption = await screen.findByRole('option', { name: /United States.*\(US\)/ });
    await user.click(usOption);
    expect(onChange).toHaveBeenCalledWith('US');
  });

  it('countries data has the expected shared dial codes that triggered #975', () => {
    // Sanity check: if these dupes ever disappear from the data, the regression
    // tests above lose their teeth. Fail noisily if the dataset shape changes.
    const phoneCounts = new Map<string, number>();
    for (const c of countries) {
      phoneCounts.set(c.phone, (phoneCounts.get(c.phone) ?? 0) + 1);
    }
    expect(phoneCounts.get('61')).toBeGreaterThanOrEqual(2);
    expect(phoneCounts.get('1')).toBeGreaterThanOrEqual(2);
    expect(phoneCounts.get('44')).toBeGreaterThanOrEqual(2);
  });
});

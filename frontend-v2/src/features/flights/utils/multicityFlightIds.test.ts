import { describe, it, expect } from 'vitest';
import { parseMulticityFlightId } from './multicityFlightIds';

describe('parseMulticityFlightId', () => {
  it('parses leg index and fare source code', () => {
    expect(parseMulticityFlightId('2::BASE64CODE')).toEqual({
      legIndex: 2,
      fareSourceCode: 'BASE64CODE',
    });
  });

  it('returns null for plain ids', () => {
    expect(parseMulticityFlightId('only-fare-code')).toBeNull();
  });

  it('returns null for invalid leg index', () => {
    expect(parseMulticityFlightId('abc::x')).toBeNull();
  });
});

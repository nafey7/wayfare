import { describe, it, expect } from 'vitest';
import { generateClientVoyaReference } from './voyaClientReference';

describe('generateClientVoyaReference', () => {
  it('uses VOYA prefix and 10-character id from allowed alphabet', () => {
    const r = generateClientVoyaReference();
    expect(r).toMatch(/^VOYA-[A-Z2-9]{10}$/);
  });
});

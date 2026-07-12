/**
 * Uniqueness and prefix checks for `LANDING_PAGE_IDS`.
 * When adding indexed registry functions, extend `collectFunctionSampleIds` per `docs/LANDING_DOM_IDS.md`
 * (`frontend-v2/docs/LANDING_DOM_IDS.md`).
 */
import { describe, it, expect } from 'vitest';

import { LANDING_PAGE_IDS } from './landingPageIds';

function collectStringIds(value: unknown, out: string[] = []): string[] {
  if (typeof value === 'string') {
    out.push(value);
    return out;
  }
  if (value && typeof value === 'object') {
    for (const v of Object.values(value as Record<string, unknown>)) {
      if (typeof v === 'function') continue;
      collectStringIds(v, out);
    }
  }
  return out;
}

/**
 * Sample ids produced by registry functions (indexed slugs).
 * Ranges are intentionally wider than current UI counts so collisions across indices or vs static strings
 * are more likely to be caught; extend further when adding new indexed helpers.
 */
function collectFunctionSampleIds(): string[] {
  const ids: string[] = [];
  const H = LANDING_PAGE_IDS;
  const n = 12;

  for (let i = 0; i <= n; i++) ids.push(H.hero.search.suggestionChip(i));

  for (let i = 0; i <= n; i++) {
    ids.push(H.weekendRail.tripCard(i));
    ids.push(H.fromCityRail.tripCard(i));
    ids.push(H.interestRail.chip(i));
    ids.push(H.interestRail.tripCard(i));
  }

  return ids;
}

describe('LANDING_PAGE_IDS', () => {
  it('uses landing- prefix and has no duplicate ids in the registry', () => {
    const ids = [...collectStringIds(LANDING_PAGE_IDS), ...collectFunctionSampleIds()];

    for (const id of ids) {
      expect(id.startsWith('landing-'), `expected landing- prefix: ${id}`).toBe(true);
    }
    expect(new Set(ids).size).toBe(ids.length);
  });
});

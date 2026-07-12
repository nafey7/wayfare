// Screenshot helper for walkthroughs.
//
// Produces a stable, branch-and-flow-namespaced output dir so M-track migration PRs
// can compare BEFORE shots (taken from origin/main staging) and AFTER shots (taken
// from staging post-deploy of the PR) without filename collisions.
//
// Output layout:
//   .local/journal/<YYYY-MM-DD>/screenshots/walkthroughs/<branch>/<flow>/<NN>-<step>.png
//
// `<branch>` is the active git branch; `<flow>` is whatever the walkthrough passes;
// `<NN>` is a 2-digit ordinal so screenshots sort the way they were captured.

import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

/**
 * @param {object} options
 * @param {string} options.flow — flow name (e.g. "flight-search-auth-first")
 * @param {string} [options.branch] — override branch detection (e.g. for CI)
 * @param {string} [options.label] — optional extra path segment ("before", "after")
 * @returns {(eventName: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>}
 */
export function makeStepScreenshotter({ flow, branch, label }) {
  const date = new Date().toISOString().slice(0, 10);
  const detectedBranch =
    branch ||
    process.env.WALKTHROUGH_BRANCH ||
    safeBranch();
  const labelSegment = label ? `${label}/` : '';

  // .local/journal lives at the repo root (worktree root via symlink).
  // Resolve from this file's location.
  const repoRoot = path.resolve(import.meta.dirname, '../../..');
  const outDir = path.join(
    repoRoot,
    '.local',
    'journal',
    date,
    'screenshots',
    'walkthroughs',
    detectedBranch,
    `${labelSegment}${flow}`,
  );
  fs.mkdirSync(outDir, { recursive: true });

  let counter = 0;

  return async function stepScreenshotter(eventName, { page }) {
    counter += 1;
    const filename = `${String(counter).padStart(2, '0')}-${eventName}.png`;
    const filepath = path.join(outDir, filename);
    await page.screenshot({ path: filepath, fullPage: false });
    return { event: eventName, filepath };
  };
}

function safeBranch() {
  try {
    const branch = execSync('git rev-parse --abbrev-ref HEAD', {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    }).trim();
    // Branch names with slashes (origin/main, fix/foo) are fine on disk.
    return branch || 'unknown';
  } catch {
    return 'unknown';
  }
}

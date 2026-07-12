#!/usr/bin/env python3
"""Pre-commit wrapper for detect-secrets.

Runs detect-secrets-hook to catch NEW secrets but silently reverts
line-number-only baseline updates that cause merge conflicts across PRs.

Exit codes from detect-secrets-hook:
  0 = clean, no issues
  1 = new secret found (must block commit) OR baseline file is unstaged
  3 = baseline was updated (line-number drift only, no new secrets)

This wrapper converts exit 3 to 0 and restores the original baseline,
because CI auto-regenerates the baseline on main
(.github/workflows/refresh-secrets-baseline.yml).
"""

import shutil
import subprocess
import sys
import tempfile

BASELINE = ".secrets.baseline"


def main() -> int:
    # Save original baseline before the hook potentially modifies it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name
    shutil.copy2(BASELINE, tmp_path)

    try:
        result = subprocess.run(
            ["detect-secrets-hook", "--baseline", BASELINE, *sys.argv[1:]],
            capture_output=True,
            text=True,
        )
        rc = result.returncode

        if rc == 3:
            # Exit 3 means the baseline was updated for line-number drift only
            # (no new secrets). We restore the original baseline below and
            # treat this as success. CI will refresh the baseline on main.
            # Suppress the misleading "please git add" message.
            return 0

        # For all other exit codes, print the original output so developers
        # see secret detection warnings (exit 1) or clean pass (exit 0).
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)

        return rc
    finally:
        # Always restore original baseline to prevent "files modified" noise.
        # If new secrets were found (exit 1), the error is already printed to
        # stderr so the developer knows what to fix.
        shutil.copy2(tmp_path, BASELINE)


if __name__ == "__main__":
    raise SystemExit(main())

---
name: review-prs
description: Launch batch PR reviews in tmux - creates git worktrees and Claude Code sessions for open PRs
disable-model-invocation: true
argument-hint: [count|pr-numbers]
---

# /review-prs - Batch PR Review in tmux

Launch Claude Code review sessions for open GitHub PRs, each in its own tmux window with an isolated git worktree.

## Usage
```
/review-prs              # Review oldest 10 open PRs
/review-prs 5            # Review oldest 5 open PRs
/review-prs 337 338 350  # Review specific PR numbers
```

## What It Does

1. Lists open PRs via `gh pr list`
2. Creates a **git worktree** per PR branch in `/tmp/pr-worktrees/<pr-number>/`
3. Creates a **single tmux session** (`pr-reviews`) with one **named window per PR** (`pr-337`, `pr-338`, etc.)
4. Launches **Claude Code** in each window with a read-only review prompt
5. Reviews are launched **one at a time** with monitoring between each
6. After each review completes, presents findings to the user for approval before taking any action

## Architecture

```
tmux session: pr-reviews
├── window: pr-337  →  worktree: /tmp/pr-worktrees/337  →  claude reviewing PR #337
├── window: pr-338  →  worktree: /tmp/pr-worktrees/338  →  claude reviewing PR #338
└── ...
```

## tmux from Claude Code's Bash Tool — Key Gotchas

### send-keys text injection fails (non-TTY)

**CRITICAL**: In Claude Code's Bash tool environment (non-TTY), `tmux send-keys` silently fails for text — keys are swallowed and never reach the pane. This is because the Bash tool runs without a real TTY (`tty` returns "not a tty"). The exit code is 0 but nothing happens.

**Solution**: Use `load-buffer` + `paste-buffer` for text, and `send-keys` only for control keys:

```bash
# BROKEN — text never reaches the pane (silent failure, exit 0):
tmux send-keys -t session:window "echo hello" C-m

# WORKING — paste-buffer bypasses the TTY requirement:
tmux_send() {
    local target=$1
    local cmd=$2
    echo "$cmd" | tmux load-buffer -
    tmux paste-buffer -t "$target"
    tmux send-keys -t "$target" C-m  # Control keys still work
}
tmux_send "session:window" "echo hello"
```

**Why**: `send-keys` injects keystrokes through tmux's input handling, which requires a valid client TTY context. `paste-buffer` writes directly to the pane's input buffer, bypassing client requirements.

**Control keys work**: `send-keys` with `C-m` (Enter), `C-c` (interrupt), `Escape`, etc. works fine — only text injection is broken.

### All tmux commands must run from a script

Because of the non-TTY environment, always wrap tmux operations in a script and execute with `bash /tmp/script.sh`. Running tmux commands directly from Claude Code's Bash tool produces `no current client` errors on stdout that pollute output.

### Enter must be a separate argument

When `send-keys` does work (e.g. from a real terminal), Enter must always be a separate argument:

```bash
# CORRECT:
tmux send-keys -t pane "text" Enter

# ALSO CORRECT:
tmux send-keys -t pane "text" C-m

# BROKEN:
tmux send-keys -t pane "text\n"
```

This is documented as the #1 gotcha by both [obra/superpowers-lab](https://github.com/obra/superpowers-lab) and [dbmcco/claude-agent-toolkit](https://github.com/dbmcco/claude-agent-toolkit).

## Environment Requirements

When launching Claude Code in a tmux pane, these environment variables must be handled:

1. **`CLAUDECODE`** — Set to `1` by the parent Claude Code session (added in v0.2.47). Nested sessions refuse to start with error: "Claude Code cannot be launched inside another Claude Code session." Must `unset CLAUDECODE` before launching `claude`. See [claude-code#531](https://github.com/anthropics/claude-code/issues/531).

2. **`SHELL`** — If set to `zsh` with Powerlevel10k instant prompt enabled, p10k's instant prompt redirects stdin early in shell startup and swallows all tmux input. Set `export SHELL=/bin/bash` before creating the tmux session. The bash shell may show `.bashrc` errors — these are harmless.

3. **`TMUX`** — Should be unset in the script that creates the tmux session to avoid nesting issues.

## Launching Claude Code in tmux — Complete Pattern

```bash
#!/bin/bash
# launch-pr-review.sh — must be run via: bash /tmp/launch-pr-review.sh
unset TMUX
unset CLAUDECODE
export SHELL=/bin/bash

# Helper: send text to tmux pane (works in non-TTY environments)
tmux_send() {
    local target=$1
    local cmd=$2
    echo "$cmd" | tmux load-buffer -
    tmux paste-buffer -t "$target"
    tmux send-keys -t "$target" C-m
}

# 1. Create tmux session (SHELL=/bin/bash ensures bash, not zsh)
tmux new-session -d -s pr-reviews -n "pr-337" -c /tmp/pr-worktrees/337
sleep 5  # Wait for shell init + MOTD

# 2. Set PATH (default bash login may not have full PATH) and launch claude
tmux_send "pr-reviews:pr-337" \
  'export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/v22.14.0/bin:/usr/local/bin:/usr/bin:/bin:$PATH" && unset CLAUDECODE && claude --allowedTools Read Grep Glob Task "Bash(gh pr view *)" "Bash(gh pr diff *)" "Bash(gh pr checks *)" --disallowedTools Edit Write "Bash(gh pr comment *)" "Bash(gh pr merge *)" "Bash(git push *)" --append-system-prompt "READ-ONLY review. Never comment, merge, or edit." "Review PR #337..."'

# 3. Accept effort-level dialog (first-run only)
sleep 15
tmux send-keys -t "pr-reviews:pr-337" C-m  # Control key — works fine

# 4. Monitor with capture-pane (from script context)
tmux capture-pane -t "pr-reviews:pr-337" -p -S -50
```

## Monitoring Reviews

### Check script

All monitoring must run from a script (non-TTY tmux client issue):

```bash
cat > /tmp/check-pane.sh << 'CHECKEOF'
#!/bin/bash
unset TMUX
unset CLAUDECODE
export SHELL=/bin/bash
tmux capture-pane -t "pr-reviews:pr-${1}" -p -S -${2:-50}
CHECKEOF

# Usage:
bash /tmp/check-pane.sh 337      # last 50 lines of PR 337 window
bash /tmp/check-pane.sh 337 100  # last 100 lines
```

### Stuck detection

Save last captured output and compare to detect stuck sessions (pattern from [dbmcco/claude-agent-toolkit](https://github.com/dbmcco/claude-agent-toolkit)):

```bash
STATE_DIR=/tmp/pr-review-state
mkdir -p "$STATE_DIR"

check_stuck() {
    local pr=$1
    local current
    current=$(tmux capture-pane -t "pr-reviews:pr-${pr}" -p -S -10)
    local last_file="${STATE_DIR}/pane-${pr}-last.txt"

    if [ -f "$last_file" ]; then
        local last
        last=$(cat "$last_file")
        if [ "$current" = "$last" ]; then
            echo "WARNING: PR #${pr} — no output change (possibly stuck)"
            return 1
        fi
    fi
    echo "$current" > "$last_file"
    return 0
}
```

### Completion detection

Pattern-match capture-pane output to detect when a review is done:

```bash
check_done() {
    local pr=$1
    local output
    output=$(tmux capture-pane -t "pr-reviews:pr-${pr}" -p -S -5)
    # Claude Code shows the input prompt "❯" when idle/done
    if echo "$output" | grep -q '^\s*❯\s*$'; then
        return 0  # Done
    fi
    return 1  # Still working
}
```

### Recovery

If a session gets stuck (pattern from dbmcco):

```bash
recover_pane() {
    local pr=$1
    # Capture full state for debugging
    tmux capture-pane -t "pr-reviews:pr-${pr}" -p -S -100 \
        > "/tmp/pr-review-state/stuck-${pr}-$(date +%s).log"
    # Double C-c to interrupt
    tmux send-keys -t "pr-reviews:pr-${pr}" C-c
    sleep 1
    tmux send-keys -t "pr-reviews:pr-${pr}" C-c
    sleep 1
    # Clear and re-prompt if needed
    tmux_send "pr-reviews:pr-${pr}" "clear"
}
```

## Permission Model

Claude Code sessions are launched with restricted tools:

**Allowed** (auto-approved):
- `Read`, `Grep`, `Glob`, `Task` — code exploration
- `Bash(gh pr view *)`, `Bash(gh pr diff *)`, `Bash(gh pr checks *)` — PR metadata
- `Bash(git log *)`, `Bash(git show *)`, `Bash(git diff *)` — git history

**Denied** (blocked):
- `Edit`, `Write`, `NotebookEdit` — no file modifications
- `Bash(gh pr comment *)`, `Bash(gh pr review *)` — no PR comments
- `Bash(gh pr merge *)`, `Bash(gh pr close *)` — no merging/closing
- `Bash(git push *)` — no pushing

## Review Prompt

Each Claude Code session is given a prompt that asks for:
1. Summary of changes
2. Code quality issues
3. Potential bugs
4. Security concerns
5. Test coverage gaps
6. Suggestions with file:line references
7. **Recommendation**: APPROVE, APPROVE WITH COMMENTS, or REQUEST CHANGES
8. **Draft PR comment** in markdown, ready to post

## Post-Review Workflow

After each review completes, the orchestrating session should:
1. Capture the review output from the tmux pane
2. Present findings to the user
3. Ask the user for a course of action:
   - Post the draft comment on the PR
   - Approve/merge the PR
   - Request changes
   - Skip (no action)
4. Execute only the approved action

## Cleanup

```bash
# Remove worktrees (from repo root)
cd /path/to/repo
for dir in /tmp/pr-worktrees/*/; do
  pr=$(basename "$dir")
  git worktree remove "/tmp/pr-worktrees/$pr" --force 2>/dev/null
done
rmdir /tmp/pr-worktrees 2>/dev/null

# Kill tmux session
tmux kill-session -t pr-reviews 2>/dev/null
```

## Useful tmux Commands

```bash
tmux attach -t pr-reviews          # Attach to review session
# Ctrl+B, n                        # Next window
# Ctrl+B, p                        # Previous window
# Ctrl+B, 0-9                      # Jump to window by index
# Ctrl+B, d                        # Detach
tmux list-windows -t pr-reviews    # List all windows
tmux kill-session -t pr-reviews    # Kill everything
```

## Alternative: Claude Code Agent Teams (Built-in)

Claude Code v0.2.47+ has experimental built-in agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). This provides native multi-agent orchestration with shared task lists and mailbox messaging, but is less customizable than the tmux approach for specific workflows like batch PR reviews.

## References

- [obra/superpowers-lab](https://github.com/obra/superpowers-lab) — tmux wrapper for interactive CLI tools in Claude Code
- [dbmcco/claude-agent-toolkit](https://github.com/dbmcco/claude-agent-toolkit) — multi-AI orchestration via tmux panes
- [Claude Code Agent Teams docs](https://code.claude.com/docs/en/agent-teams) — built-in multi-agent feature
- [CLAUDECODE env var — claude-code#531](https://github.com/anthropics/claude-code/issues/531)

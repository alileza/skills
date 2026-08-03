---
name: token-setup
description: Guided setup of the token-reduction stack — save a usage baseline, install the companion skills, set up context visibility in the statusline, and optionally add output-trimming and budget hooks. Use when the user wants to set up token reduction, install these skills, or invokes /token-setup.
---

# Token setup: install the reduction stack, with a baseline first

You are setting up the user's environment. Show each step before doing it, ask
which optional pieces they want, and verify every install. Never skip the baseline
— without a before, the after means nothing.

## Step 0 — Baseline (always, first, no permission needed)

```bash
mkdir -p ~/.claude/usage-baselines
npx -y ccusage@latest daily --json > ~/.claude/usage-baselines/baseline-$(date +%Y-%m-%d).json
```

Tell the user this snapshot is what `/token-audit` will compare against later.
If a baseline from a previous run already exists, keep it — don't overwrite.

## Step 1 — Ask what to install

Present the menu (AskUserQuestion, multiSelect) with one-line expected impact each:

1. **Companion skills** (delegate-exploration, scoped-read, quiet-verify,
   task-boundary, token-audit) — behavioral discipline; zero risk; recommended.
2. **Context visibility in the statusline** — see context size grow, so /clear
   becomes a habit; recommended.
3. **Output-trimming hook** — enforcement for success-noise trimming; only worth it
   if an audit showed large passing-test output.
4. **Session budget circuit-breaker hook** — hard per-session ceiling; for users who
   want a guarantee, not a nudge.

If the user has already run `/token-audit`, match recommendations to its findings
instead of the generic defaults.

## Step 2 — Install what was picked

**Companion skills.** If this repo is already cloned locally, symlink each skill
directory into `~/.claude/skills/` (symlinks pick up repo updates). Otherwise:

```bash
git clone https://github.com/alileza/skills ~/.claude/skills-repo
for s in delegate-exploration scoped-read quiet-verify task-boundary token-audit token-setup; do
  ln -sfn ~/.claude/skills-repo/$s ~/.claude/skills/$s
done
```

**Statusline.** If claude-hud is already installed, run its setup skill. Otherwise
check the user's current statusline setting before touching it — never silently
replace an existing statusline; show what's there and ask.

**Output-trimming hook (PostToolUse).** Write a small script that receives the hook
JSON on stdin and, for Bash results from test/build commands with exit code 0,
returns `updatedToolOutput` with a one-line summary; on nonzero exit it returns
nothing (output passes through verbatim). Register it in `~/.claude/settings.json`
under `hooks.PostToolUse` with a Bash matcher. Constraints that MUST hold:
- Prefer rewriting over blocking — a denied/blocked call costs a full extra turn,
  which re-bills the whole accumulated context.
- Hook output is capped at 10,000 chars.
- Hooks fire inside subagents too — check `agent_id` in the payload and pass
  subagent output through untouched, or trimming happens twice.
- Never trim failure output.

**Budget circuit-breaker (PostToolBatch).** A script that reads the session's token
totals and exits 2 (stopping the loop with a message) past a user-chosen ceiling.
Confirm the ceiling with the user; default to something generous (e.g. 2× their
median session from the baseline) — this is a parachute, not a leash.

Consult current Claude Code hooks documentation for exact payload fields before
writing either hook; verify with a dry run (`echo '<sample json>' | script`) before
registering it.

## Step 3 — Verify

- `ls -la ~/.claude/skills/` — symlinks resolve.
- Skills appear in the available-skills list (may need a new session).
- Hooks: trigger a cheap matching tool call and confirm the rewrite happened.
- Show the user a one-screen summary: what was installed, where, how to undo each
  piece (every install must be reversible with a single rm/edit).

## Step 4 — Hand off to the loop

Tell the user: work normally for ~a week, then run `/token-audit` to compare
against the baseline saved in Step 0 — judged by cost per completed task, not raw
tokens. Anything that didn't pay for itself, come back and remove.

## Don'ts

- Don't install everything unconditionally — the menu exists because hooks have
  real failure modes and most users only need the skills + statusline.
- Don't overwrite an existing statusline, hook, or settings entry without showing
  the user the diff first.
- Don't invent hook payload fields from memory — check the docs, dry-run the script.

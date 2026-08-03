---
name: reduce-token-usage
description: Analyze Claude Code token usage, find where the tokens actually go, and guide the user through the matching fix — session habits, statusline visibility, enforcement hooks, code-graph retrieval, context management. Use when the user asks why usage is high, wants to reduce token spend or set up token reduction, or invokes /reduce-token-usage.
---

# Reduce token usage: measure, diagnose, fix, verify

You are auditing the user's real usage and changing their environment. Gather data
first; every recommendation must point at a number you found. Show each change
before making it, and make every install reversible.

## The cost model (frame every finding with this)

**Cost ≈ context size × turns.** Every turn re-sends the full accumulated context as
input; cache reads are typically >90% of all tokens. The levers that matter shrink
*what accumulates in context* (file reads, tool output, images) or *how many turns
re-bill it* (session length). Output-side tricks (terse prompting) target ~1% of
spend and can be net negative by causing extra edit-test-edit cycles.

## Step 1 — Measure

Save a baseline first if none exists (never overwrite an old one — it's the "before"):

```bash
mkdir -p ~/.claude/usage-baselines
npx -y ccusage@latest daily --json > ~/.claude/usage-baselines/baseline-$(date +%Y-%m-%d).json
npx -y ccusage@latest session 2>/dev/null | tail -30
```

Then profile *where context comes from*: find the largest transcripts under
`~/.claude/projects/`, inspect one JSONL line to learn the shape, then measure —
largest tool results, result bytes per tool, most re-read files, scoped vs
whole-file reads, user turns per session, session date spans. Adapt jq to the
actual shape; if a command fails, say so and continue — don't fake numbers.

## Step 2 — Diagnose

Classify into buckets and report the split with evidence:

| Symptom in the data | Diagnosis |
|---|---|
| Sessions spanning many days/tasks; hundreds of turns in one context | **No task boundaries** — usually the dominant cost |
| Many large whole-file Reads; exploratory reads of files never edited | **Exploration bloat** |
| Huge Bash results from test/build runs that passed | **Success noise** |
| Images/screenshots/design exports held in long-lived context | **Heavy artifacts** |
| Files >2,000 lines re-read constantly | **Monolith hot files** — a repo problem, not a tooling problem |
| High turn count vs work done (denials, retries, rework) | **Turn churn** |

## Step 3 — Fix (matched to the diagnosis, user picks)

Present what the data supports, with expected impact; install only what the user
confirms. Never overwrite an existing statusline, hook, or settings entry without
showing the diff.

**No task boundaries → the companion skill + visibility.**
Install [clear-context-between-tasks](../clear-context-between-tasks/SKILL.md) and
a statusline showing context size (e.g. claude-hud) so growth is visible and
/clear becomes a habit. For a hard guarantee, add a **PostToolBatch budget
circuit-breaker**: a script that sums each batch's `tool_results[].tool_use_tokens`
(live counts — the transcript file lags) into a per-session state file and emits
`{"decision":"block", "reason":..., "systemMessage":...}` past a generous ceiling
(~2× a heavy day-session; a parachute, not a leash). Verify payload fields against
current hooks docs and dry-run against a sample payload before registering in
`~/.claude/settings.json` under `hooks.PostToolBatch`.

**Exploration bloat → habits first, then indexing.**
Habits (teach, don't install): delegate open-ended searches to a subagent so only
conclusions enter the main context; locate with Grep/Glob/LSP before reading;
Read with offset/limit windows on files over ~200 lines; never Read a file just
to search it. If the repo is large (500+ files) and the habits aren't enough,
add a **code-graph retrieval MCP server** (e.g. graphify) — pre-indexes the repo
so Claude queries structure instead of reading to orient. Verify the tool's
current install method and maintenance status first, build the graph, confirm
incremental updates work. Published claims run 49–70×; real replays measure
single-digit percent — only the user's own before/after decides.

**Success noise → filter at the shell; hook only if large.**
Habit: capture command output, branch on exit code — successes become one line
("PASS, N lines suppressed"), failures pass through verbatim, never trimmed or
summarized. If the audit shows large passing-run output, enforce with a
**PostToolUse hook** returning `updatedToolOutput`. Hook rules: rewrite, never
block (a blocked call costs a full extra turn re-billing the whole context);
output caps at 10,000 chars; hooks fire inside subagents — check the payload and
pass subagent output through untouched.

**Heavy artifacts →** do image/design iteration in short dedicated sessions; never
re-read an image already in the conversation.

**Monolith hot files →** recommend splitting them into feature modules — the one
durable repo-side fix; every future session benefits with zero tooling.

**Turn churn →** fix the cause: run /fewer-permission-prompts for denials;
tighter task specs for rework. Do not recommend terse-output prompting.

## Step 4 — Verify and close the loop

Verify each install (symlinks resolve, hooks fire on a cheap matching call), then
show a one-screen summary: what was installed, where, and the one-line undo for
each. Tell the user: work normally for ~a week, re-run /reduce-token-usage, and
compare against the baseline by **cost per completed task** (counting rerun tax),
not raw tokens. Anything that didn't pay for itself gets removed — say so plainly.

## Don'ts

- Don't build or install another usage analyzer — ccusage suffices.
- Don't quote published headline savings; only claim what the user's own data shows.
- Don't install anything unconditionally — every fix is gated on a measured symptom.
- Don't invent hook payload fields or install commands from memory — check current
  docs, dry-run scripts before registering.

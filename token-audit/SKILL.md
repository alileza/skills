---
name: token-audit
description: Analyze Claude Code token usage — for this session or recent history — find where the tokens actually go, and guide the user through installing the right fix (code-graph retrieval, output-trimming hooks, context discipline). Use when the user asks why usage is high, wants to reduce token spend, or invokes /token-audit.
---

# Token audit: measure, diagnose, then install the right fix

You are auditing the user's real usage, not reciting generic advice. Gather data
first; every recommendation must point at a number you found.

## The cost model (frame every finding with this)

**Cost ≈ context size × turns.** Every turn re-sends the full accumulated context as
input. Cache reads typically account for >90% of all tokens — so the levers that
matter shrink *what accumulates in context* (file reads, tool output) or *how many
turns re-bill it*. Output-side tricks (terse prompting) target ~1% of spend and can
be net negative by causing extra edit-test-edit cycles.

## Step 1 — Gather

Run these and keep the results:

```bash
# Historical spend, per day and per model
npx -y ccusage@latest daily --json

# Session-level: which sessions were expensive
npx -y ccusage@latest session 2>/dev/null | tail -30
```

Then profile *where context comes from* in recent transcripts
(`~/.claude/projects/<current-project-dir>/*.jsonl`, newest first):

```bash
# Largest single tool results in a transcript (the context bloat culprits)
jq -r 'select(.toolUseResult != null) | [(.toolUseResult | tostring | length), (.message.content[0].content[0].text // "" | tostring | .[0:80])] | @tsv' <transcript>.jsonl | sort -rn | head -15

# Files read repeatedly in one session (each re-read re-bills)
jq -r 'select(.message.content[0].input.file_path? != null) | .message.content[0].input.file_path' <transcript>.jsonl | sort | uniq -c | sort -rn | head -10
```

Adapt the jq to the actual transcript shape — inspect one line first. If a command
fails, say so and continue with what you have; don't fake numbers.

## Step 2 — Diagnose

Classify the spend into these buckets and report the split with evidence:

| Symptom in the data | Diagnosis |
|---|---|
| Many large whole-file Read results; exploratory reads of files never edited | **Exploration bloat** — the biggest and most common sink |
| Huge Bash results from test/build runs that passed | **Success noise** |
| Single sessions spanning many unrelated tasks; cost per session climbing | **No task boundaries** — context never resets |
| High turn count relative to work done (denied tools, retries, edit-test-edit loops) | **Turn churn** — each extra turn re-bills everything |

## Step 3 — Recommend and install

Match the fix to the dominant bucket. Present options with expected impact, then
install what the user picks (these change their environment — confirm before
installing).

**Exploration bloat → code-graph retrieval + subagent delegation.**
The biggest shipped lever for large repos: a code-graph/retrieval MCP server
(e.g. graphify, codegraph — search for a current, maintained one; verify before
recommending a specific package) collapses "read five files to find the right one"
into one indexed query. Install via `claude mcp add`. Pair with the
`delegate-exploration` skill from this repo so open-ended searches run in a
subagent and only conclusions enter the main context.

**Success noise → output filtering, enforced by hook.**
The `quiet-verify` skill covers discipline; for a guarantee, add a **PostToolUse
hook** that returns `updatedToolOutput` to trim passing test/build output
(failures pass through verbatim). Prefer rewriting over blocking — a denied call
costs a full extra turn, which re-bills the whole context. Hook gotchas: output
is capped at 10,000 chars; hooks also fire inside subagents, so check `agent_id`
to avoid double-processing; `transcript_path` lags the in-memory conversation.

**No boundaries → task-boundary skill + visibility.**
Install the `task-boundary` skill, and a statusline that shows current context
size (e.g. claude-hud) so the user *sees* growth. For a hard ceiling, a
**PostToolBatch hook** exiting 2 is the right circuit-breaker for a per-session
budget.

**Turn churn → fix the cause, not the symptom.**
Usually permission denials (run `/fewer-permission-prompts`) or vague task specs
causing rework. Do not recommend terse-output prompting; it trades cheap output
tokens for expensive extra turns.

## Step 4 — Close the loop

Save a dated ccusage JSON snapshot to `~/.claude/usage-baselines/` before anything
is installed. Tell the user to re-run `/token-audit` after ~a week of normal work;
compare **cost per completed task** (counting rerun tax), not raw tokens. If an
intervention didn't pay for itself, recommend removing it — say so plainly.

## Don'ts

- Don't recommend building or installing another usage *analyzer* — that space is
  saturated (ccusage suffices).
- Don't quote published headline savings (49×, 70×); only claim what the user's own
  before/after shows.
- Don't install anything without showing the user what and why first.

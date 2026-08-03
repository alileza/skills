---
name: task-boundary
description: Use when a task is verifiably complete AND the user starts something unrelated in the same session — a clear boundary between finished work and new work. Summarize what must carry forward, then suggest the user run /clear or /compact. Never fires mid-task or on a follow-up to the current task.
---

# Task boundaries: declare what to keep, then clear

## Why

Cost ≈ context size × turns. Context only grows within a session — every finished
task's file reads, test output, and dead ends keep getting re-sent as input for the
rest of the session. The single biggest lever a user has is starting new work with a
small context. But clearing loses state, so the state worth keeping must be written
down *first*.

## When a boundary exists

ALL of the following, not some:

1. The previous task is **done and verified** (tests pass, change committed, question
   answered) — not paused, not blocked, not "probably fine".
2. The user's new message starts **unrelated work** — different feature, different
   repo area, different question. A follow-up, review pass, or "also fix X nearby" is
   the *same* task.
3. The session context is substantial — many files read, long tool outputs
   accumulated. Early in a session, clearing saves nothing.

If in doubt, there is no boundary. A wrong clear costs the user real state; a missed
clear costs only tokens.

## What to do at a boundary

1. Write a short handoff of what carries forward — decisions made, constraints
   discovered, file paths that matter, anything not recoverable from the repo or git
   history. Put durable facts in memory or a NOTES file, not just prose.
2. Then tell the user: this is a good point to `/clear` (unrelated new work) or
   `/compact` (loosely related), and that the carry-forward is saved.
3. **Do not clear anything yourself.** The user decides. Your job is making the
   boundary visible and the clear safe.

## Anti-patterns

- Suggesting a clear mid-task because context "feels large" — the rerun tax of lost
  state exceeds the token savings.
- Writing a handoff so long it recreates the context it was meant to replace. Keep it
  under ~30 lines.
- Treating every new user message as a boundary. Most messages continue the task.

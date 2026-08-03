---
name: delegate-exploration
description: Use when a task requires open-ended search or exploration of a codebase — finding where something is implemented, understanding how a subsystem works, locating all usages of a pattern, or any search where you don't know in advance which files matter. Delegate the search to a subagent instead of reading files into the main context.
---

# Delegate exploration to subagents

## Why

Every file you read into the main conversation is re-sent as input on **every subsequent turn**. A 2,000-line file read early in a session gets re-billed dozens of times. Exploration is the worst offender: most of what you read while searching turns out to be irrelevant, but it stays in context forever.

A subagent explores in its own context and returns only the conclusion. The dead-end reads are billed once, in the subagent, and never again.

## When to delegate

Delegate to an `Explore` (or general-purpose) agent when:

- You don't know which files are relevant yet ("where is X handled?", "how does Y work?").
- The answer requires sweeping many files, directories, or naming conventions.
- You need a summary or a map, not the file contents themselves.
- You expect to read more than ~2 files just to orient yourself.

## When NOT to delegate

Read directly when:

- You already know the exact file (and ideally the region) you need.
- You are about to **edit** the file — the editing context needs the real content.
- It's a single-fact lookup one Grep/Glob away.

## How

1. Give the subagent a precise question and the form of answer you want back:
   file paths with line numbers, a short structural summary, or a yes/no with evidence.
2. Ask for **conclusions, not contents**: "Return the list of files and the 5-line
   relevant excerpt from each, not whole files."
3. When the subagent returns, read *only* the specific regions it identified, and only
   if you actually need them in the main context (e.g. to edit them).

## Anti-patterns

- Delegating, then re-running the same search yourself in the main context.
- Asking the subagent to "paste the relevant code" wholesale — that just moves the
  bloat one hop before it lands in your context anyway.
- Spawning a subagent for a lookup you could answer with one targeted Grep.

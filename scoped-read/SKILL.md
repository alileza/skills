---
name: scoped-read
description: Use whenever reading source files during a task — before any Read call on a file you haven't fully mapped, especially files over ~200 lines. Locate the relevant region first (Grep, Glob, LSP, ctags), then read only that region with offset/limit instead of the whole file.
---

# Scoped reads: locate, then read

## Why

File reads are where the tokens are. A whole-file Read of a large module can cost more
than all the prose in a session combined — and it is re-sent as input on every later
turn. Reading 80 relevant lines instead of 1,500 is a ~95% reduction on that file,
compounded across every remaining turn.

## The discipline

1. **Locate first.** Use Grep (with `-n` line numbers), Glob, or LSP
   (go-to-definition / find-references) to find *where* in the file the relevant code
   lives. A search result with line numbers is cheap; a full file is not.
2. **Read a window.** Call Read with `offset` and `limit` around the located region.
   Include enough surrounding context to edit safely — the enclosing function or
   class, its imports if you'll reference them — but not the whole file.
3. **Widen deliberately, not defensively.** If the window turns out to be too small,
   read the adjacent window. Two scoped reads are still far cheaper than one
   whole-file read.

## When a full read is correct

- The file is small (under ~200 lines) — scoping overhead isn't worth it.
- You are about to make edits scattered across the whole file.
- It's a config/manifest file whose structure you need in full.

## Rules of thumb

- Never Read a file just to find something in it — that's what Grep is for.
- Never re-Read a file already in context unless it changed on disk.
- When a Grep shows 40 matches, narrow the pattern before reading any of them.

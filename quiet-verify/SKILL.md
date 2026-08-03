---
name: quiet-verify
description: Use whenever running builds, tests, linters, or typecheckers — any command whose output is mostly success noise. Filter output at the shell so successes are counted, not printed, and failures come back verbatim.
---

# Quiet verification: failures verbatim, successes counted

## Why

A passing test run can emit thousands of lines that all mean one thing: "OK". Every
one of those lines enters context and is re-billed on every later turn. The
information content of a green run is one line. The information content of a red run
is the failure output — which you need **verbatim**, never summarized.

## The discipline

Filter at the shell, before output enters context:

```bash
# Tests: show failures fully, summarize success
go test ./... 2>&1 | tail -20          # Go already prints only failures + summary
npm test 2>&1 | grep -vE '^\s*(✓|PASS)' | tail -40

# Builds/typecheck: errors only
tsc --noEmit 2>&1 | head -50           # tsc prints nothing on success
go build ./... 2>&1                     # silent on success — run as-is

# Linters: count clean files, print dirty ones
golangci-lint run 2>&1 | head -60
```

General pattern — capture, branch on exit code:

```bash
out=$(cmd 2>&1); code=$?
if [ $code -eq 0 ]; then echo "PASS ($(echo "$out" | wc -l) lines suppressed)";
else echo "$out" | tail -80; exit $code; fi
```

## Rules

- **Never filter failure output.** If the command fails, you need the real error text
  — truncate from the top (`tail`) only when it's enormous, and say you truncated.
- Preserve the exit code; don't let a pipe swallow it (`set -o pipefail` or the
  capture pattern above).
- Don't re-run a command unfiltered "just to see" after a filtered pass — trust the
  exit code.
- Verbose flags (`-v`, `--verbose`) are for humans watching live; never use them here.

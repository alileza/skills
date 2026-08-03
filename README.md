# skills

Claude Code skills for reducing token usage — targeting where the cost actually is:
**context size × turns**. Every turn re-sends the full accumulated context as input,
and most of that context is file reads, not prose. These skills attack the input
side; output-side tricks (terse-prompting) target ~1% of spend and can be net
negative.

## The two skills

**[reduce-token-usage](reduce-token-usage/SKILL.md)** — run `/reduce-token-usage`
and Claude measures your actual usage (ccusage history plus your session
transcripts), diagnoses where the tokens go — missing task boundaries, exploration
bloat, success noise, heavy artifacts, monolith files, turn churn — and guides you
through only the fixes your data supports: session habits, statusline context
visibility, enforcement hooks (output trimming, a session budget circuit-breaker),
code-graph retrieval (e.g. graphify) for large repos, and context-management
tooling. It saves a baseline first and re-measures after a week, so every
intervention is judged by your own before/after — cost per completed task — not
published headline numbers.

**[clear-context-between-tasks](clear-context-between-tasks/SKILL.md)** — the one
always-on habit skill, because session length is usually the dominant cost. At a
verified task boundary it saves the carry-forward state, then suggests /clear. It
never clears anything itself and never fires mid-task.

## Install

```bash
git clone https://github.com/alileza/skills ~/.claude/skills-repo
ln -s ~/.claude/skills-repo/{reduce-token-usage,clear-context-between-tasks} ~/.claude/skills/
```

Then run `/reduce-token-usage` in Claude Code.

## Measure before you believe

Skills are discipline, not enforcement — the model can ignore them, and published
savings numbers (49×, 70×) rarely reproduce; real-world replays measure single-digit
percent. Record a baseline, run a comparable period, and compare **cost per
completed task**, counting any rerun tax. If an intervention doesn't pay for itself
on your own work, remove it.

## License

MIT

# skills

Claude Code skills for reducing token usage — targeting where the cost actually is:
**context size × turns**. Every turn re-sends the full accumulated context as input,
and most of that context is file reads, not prose. These skills attack the input
side; output-side tricks (terse-prompting) target ~1% of spend and can be net
negative.

## The skills

| Skill | What it does | Lever |
|---|---|---|
| [delegate-exploration](delegate-exploration/SKILL.md) | Run open-ended searches in a subagent; only conclusions enter the main context | Keeps dead-end reads out of the re-billed context. Highest expected payoff. |
| [scoped-read](scoped-read/SKILL.md) | Locate with Grep/LSP first, then Read a bounded window with offset/limit | Shrinks the dominant cost: file contents held in context |
| [quiet-verify](quiet-verify/SKILL.md) | Filter build/test output at the shell — failures verbatim, successes counted | Stops success noise from accumulating across turns |
| [task-boundary](task-boundary/SKILL.md) | At a verified task boundary, save carry-forward state and suggest /clear | Resets context growth between unrelated tasks |

## Install

```bash
git clone https://github.com/alileza/skills ~/.claude/skills-repo
ln -s ~/.claude/skills-repo/{delegate-exploration,scoped-read,quiet-verify,task-boundary} ~/.claude/skills/
```

Or copy the four directories into `~/.claude/skills/` (user-wide) or
`.claude/skills/` in a project.

## Measure before you believe

Skills are discipline, not enforcement — the model can ignore them, and published
savings numbers rarely reproduce. Before installing, record a baseline of your normal
usage (e.g. with [ccusage](https://github.com/ryoppippi/ccusage)), run a comparable
period with the skills installed, and compare **cost per completed task**, counting
any rerun tax. If an intervention doesn't pay for itself on your own work, drop it.

Known risk: `task-boundary` is the most valuable and the most likely to misfire,
since it must infer where a boundary is. If it suggests clearing mid-task, tighten
its description to require an explicit user signal.

## License

MIT

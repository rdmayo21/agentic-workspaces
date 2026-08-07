---
name: {{name}}
description: {{skill_description}}
---

# {{title}}

The canonical workspace for this project is:

`~/ai-workspaces/{{name}}/`

This skill is a thin pointer — all project knowledge lives in the workspace
files, never in this skill. Sessions may be weeks apart; the workspace IS
the memory.

## Before working

1. Read `AGENTS.md` in the workspace (conventions and file map).
2. Read `STATUS.md` and `NEXT-ACTIONS.md`.
3. Read only the additional files relevant to the request.
4. Re-verify facts that may have gone stale (prices, availability, dates,
   operating hours, rules) before relying on them.
5. Distinguish confirmed items, settled decisions, tentative choices, and
   unreviewed ideas — don't conflate them.

## After meaningful work

1. Update the relevant project files.
2. Record newly settled choices in `DECISIONS.md` with rationale.
3. Preserve source links and retrieval dates in `RESEARCH.md`.
4. Update `STATUS.md` (including its date) and `NEXT-ACTIONS.md`.
5. Never silently discard previous decisions or research — move superseded
   material to `archive/`.
6. Make it durable: run
   `python3 ~/ai-workspaces/skills/new-ai-workspace/scripts/sync.py now`
   (commits and pushes the whole workspace system to its private remote).

## Workspace maintenance

Listing, archiving, and repairing workspaces is handled by the
new-ai-workspace skill:

```
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py --help
```

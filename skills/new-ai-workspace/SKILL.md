---
name: new-ai-workspace
description: Bootstrap a persistent, provider-neutral AI workspace (~/ai-workspaces/<name>/) plus a thin project skill available in Claude Code, Codex, and Gemini CLI. USE THIS SKILL whenever the user wants to turn an idea into an ongoing multi-session project, even if they never say "workspace" — "create a workspace", "new workspace for X", "set up a persistent project for X", "make this an ongoing project", "turn this conversation into a project", "track this across sessions", "/new-ai-workspace" — and for managing the workspace system itself: "list my workspaces", "which workspaces are active", "archive the X workspace", "delete the X workspace", "repair/fix the X workspace", a broken workspace skill or symlink in Claude Code or Codex, or anything touching ~/ai-workspaces, its INDEX.md, or registry.json. ALSO USE for workspace durability and sync: "is everything backed up", "sync my workspaces", "workspace backup status", "restore my workspaces on this machine", "set up my workspaces on a new computer", conflicts between devices, or rollback of a workspace change. ALL workspace mechanics go through scripts/workspace.py and scripts/sync.py — never hand-create workspace dirs, symlinks, or git plumbing.
---

# New AI Workspace (bootstrap)

Turns an ongoing idea into four things at once:

1. A persistent workspace at `~/ai-workspaces/<name>/` — provider-neutral
   markdown files that are the project's memory, inside the git-backed
   `~/ai-workspaces` repo (your private remote), which
   is the durable asset.
2. A thin project skill at `~/.ai/skills/<name>/SKILL.md` (really
   `~/ai-workspaces/skills/<name>/` — `~/.ai/skills` is a compat symlink
   into the repo) that points to the workspace.
3. Symlinks exposing that skill to Claude Code (`~/.claude/skills/<name>`)
   and Codex (`~/.agents/skills/<name>`), so `/name` works in both.
4. A Gemini CLI command (`~/.gemini/commands/<name>.toml`), so `/name`
   works there too.

You handle judgment; `scripts/workspace.py` handles filesystem mechanics
and `scripts/sync.py` handles durability (git commit/push, backup status,
autosync). Never hand-create the directories, symlinks, registry, or git
plumbing — the scripts exist so those are identical every time, regardless
of which model runs them.

## Step 1 — Decide if this deserves a workspace

Apply the test: **will this need multiple sessions, accumulating
information, evolving decisions, or repeated workflows?**

- Yes → create a workspace + project skill (this skill).
- It's a reusable *procedure* with no persistent state (e.g.
  "compare-hotels", "review-contract") → suggest a normal skill instead
  (skill-creator), not a workspace.
- One-session task → neither; just do the task.

Global skills are a scarce resource — every one adds metadata to every
session's context in both tools. Don't let momentary ideas become permanent
residents. If unsure, say so and ask.

## Step 2 — Pick a type and shape

Types (each adds a few files on top of the base set):

- `general` — base files only (default; when in doubt, start here)
- `travel` — ITINERARY, LODGING, BOOKINGS
- `research` — QUESTIONS, FINDINGS
- `business` — THESIS, CUSTOMERS
- `investing` — INVESTMENT-THESIS, EVIDENCE, RISKS, WATCHLIST

Base set (always): AGENTS.md, STATUS.md, CONTEXT.md, DECISIONS.md,
EXPERIMENTS.md, RESEARCH.md, NEXT-ACTIONS.md, archive/.

Start minimal. Add `--extra FILE` only for files the idea clearly needs on
day one — fifteen empty files is ceremony, not value. New files can always
be added later by whichever agent needs them.

## Step 3 — Run the script

```bash
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py create <name> \
  --type <type> \
  --description "One-line description of the project" \
  --skill-description "Full trigger-rich description for the project skill" \
  [--extra FILE ...] [--status incubating] [--dry-run]
```

Write the `--skill-description` yourself, carefully — it is the ONLY thing
Claude Code and Codex see when deciding whether to load the project skill.
Make it pushy and concrete: what the workspace is, the specific nouns and
phrases that should trigger it (places, tickers, company names, "where are
we on X"), and end with "Invoke with /<name>." Look at
`assets/project-skill-template.md` and the repo's
`examples/skills/tokyo-trip/SKILL.md` for the style that works.

The script refuses to overwrite anything that exists, normalizes the name,
validates the generated SKILL.md, creates relative symlinks, and registers
the workspace in `~/ai-workspaces/registry.json` + `INDEX.md`. Trust its
error messages — if it says a name is taken, pick another; don't force it.

## Step 4 — Tailor the initial content

The script leaves template stubs. Immediately replace the stubs with real
content from what the user told you:

- `CONTEXT.md` — goals, constraints, dates, people, budgets they mentioned
- `STATUS.md` — where things actually stand today
- `NEXT-ACTIONS.md` — the real first actions, not the placeholder
- Type files — seed with anything already known (e.g. dates into ITINERARY)

Then run `python3 ~/.ai/skills/new-ai-workspace/scripts/sync.py now` so the
new workspace is durably backed up, and tell the user what was created and
that `/<name>` (Claude Code, Gemini) or `$<name>` (Codex) becomes available
when their next session starts.

## Managing existing workspaces

```bash
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py list
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py archive <name>
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py repair <name>
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py adopt <name> --type <type> --description "..."
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py delete <name> --yes
```

- `archive` retires the project: removes the skill + symlinks (freeing
  context in both tools) but keeps every workspace file, with the SKILL.md
  preserved in the workspace's `archive/`. Reversible via `repair`.
- `repair` restores anything missing (base files, SKILL.md, symlinks) and
  reactivates archived workspaces. Never overwrites existing content.
- `adopt` migrates a pre-existing project into the system without touching
  its files: place the files at `~/ai-workspaces/<name>/` and a SKILL.md at
  `~/.ai/skills/<name>/` first; adopt validates, symlinks, and registers
  them (with `managed: false`, so repair skips base-file restoration).
- `delete` permanently removes workspace + skill + links + registry entry.
  Destructive — confirm with the user before running, always.

The registry lives at `~/ai-workspaces/registry.json`; `INDEX.md` beside it
is generated output, refreshed by every command. Read INDEX.md to answer
"what workspaces do I have?" — but run `list` if freshness matters.

## Durability, sync, and recovery

The whole system (workspaces + skills + registry) is one git repo at
`~/ai-workspaces` with a private GitHub remote. Key commands:

```bash
python3 ~/.ai/skills/new-ai-workspace/scripts/sync.py status  # backed up? conflicted?
python3 ~/.ai/skills/new-ai-workspace/scripts/sync.py now     # commit + rebase + push
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py bootstrap  # new machine
```

- Run `sync.py now` after any meaningful workspace update — conversations
  are ephemeral; a pushed commit is not. Autosync (launchd, 30 min) is the
  safety net, not the primary mechanism.
- `sync.py now` refuses to commit likely secrets (tokens, SSNs, key blocks).
  Workspaces must never contain credentials — reference their location.
- Conflicts never lose work: a failed rebase pushes local state to a
  `conflict/<host>-<timestamp>` rescue branch and `status` reports it.
- Rollback is plain git (`git log -- <workspace>/`, `git checkout <sha> --`).
- Clean-machine restore: clone the repo, run `bootstrap`, install autosync —
  fully documented in `~/ai-workspaces/RECOVERY.md` (write one for your
  setup; the GitHub app covers basic mobile access).

## Captured context (inboxes)

`scripts/capture.py` files emails/links/photos/notes into `<ws>/inbox/`
(or `capture/inbox/` unsorted) with provenance frontmatter; payloads land
in `media/<ws>/`. Inbox items are staged, not accepted — sessions
incorporate them into state files per the workspace AGENTS.md "Inbox"
section, then delete them. When asked to triage captures, move items +
payloads to the right workspace and fix their `media:` paths.

For layout details, status semantics, and how discovery works in each tool,
read `references/workspace-conventions.md`.

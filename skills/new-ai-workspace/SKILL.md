---
name: new-ai-workspace
description: Bootstrap a persistent, provider-neutral AI workspace (~/ai-workspaces/<name>/) plus a thin pointer skill available in Claude Code, Codex, and Gemini CLI. USE THIS SKILL whenever the user wants to turn an idea into an ongoing multi-session project, even if they never say "workspace" — "create a workspace", "new workspace for X", "set up a persistent project for X", "make this an ongoing project", "turn this conversation into a project", "track this across sessions", "/new-ai-workspace" — and for managing the workspace system itself: "list my workspaces", "which workspaces are active", "archive the X workspace", "delete the X workspace", "repair/fix the X workspace", a broken workspace skill or symlink in Claude Code or Codex, or anything touching ~/ai-workspaces, its INDEX.md, or registry.json. ALSO USE for workspace durability and sync: "is everything backed up", "sync my workspaces", "workspace backup status", "restore my workspaces on this machine", "set up my workspaces on a new computer", conflicts between devices, or rollback of a workspace change. ALL workspace mechanics go through scripts/workspace.py and scripts/sync.py — never hand-create workspace dirs, symlinks, or git plumbing.
---

# New AI Workspace (bootstrap)

Turns an ongoing idea into four things at once:

1. A persistent workspace at `~/ai-workspaces/<name>/` — provider-neutral
   markdown files that are the project's memory, inside the git-backed
   `~/ai-workspaces` repo (your private remote), which is the durable asset.
2. A thin pointer skill at `~/.ai/skills/<name>/SKILL.md` (really
   `~/ai-workspaces/skills/<name>/` — `~/.ai/skills` is a compat symlink
   into the repo) that points to the workspace.
3. Symlinks exposing that skill to Claude Code (`~/.claude/skills/<name>`)
   and Codex (`~/.agents/skills/<name>`), so `/name` works in one and
   `$name` in the other.
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

- Yes → create a workspace + pointer skill (this skill).
- It's a reusable *procedure* with no persistent state (e.g.
  "compare-hotels", "review-contract") → suggest a normal skill instead,
  not a workspace.
- One-session task → neither; just do the task.

Skills are a scarce resource — every one adds metadata to every session's
context. Don't let momentary ideas become permanent residents. If unsure,
say so and ask.

## Step 2 — Agree on what it is before touching the filesystem

One short exchange with the user, before running anything:

- **Purpose and "done".** One sentence each. What is this project, and what
  would make it finished (or, for an ongoing area, what steady state looks
  like)?
- **What must never happen from here.** E.g. "draft emails, never send",
  "never book anything", "no purchases". These become standing rules in the
  workspace's `AGENTS.md`.
- **What's already known.** Dates, people, constraints, existing documents.
  These seed `STATUS.md` and `references/`.

This is the content of the "What this is" section in `AGENTS.md`. A
workspace created from a one-line idea accretes undeclared files and
re-derived decisions; two minutes here prevents most of that.

## Step 3 — Pick a type

Types (each adds a few files on top of the base set):

- `general` — base files only (default; when in doubt, start here)
- `travel` — ITINERARY, LODGING, BOOKINGS
- `research` — QUESTIONS, FINDINGS
- `business` — THESIS, CUSTOMERS
- `investing` — INVESTMENT-THESIS, EVIDENCE, RISKS, WATCHLIST

Base set (always): `AGENTS.md`, `STATUS.md`, `DECISIONS.md`,
`NEXT-ACTIONS.md`, `RESEARCH.md`, `references/`, `inbox/`, `archive/`.

Start minimal. Add `--extra FILE` only for files the idea clearly needs on
day one — fifteen empty files is ceremony, not value. New files can always
be added later by whichever agent needs them (and get a row in the
`AGENTS.md` file map when they are).

## Step 4 — Run the script

```bash
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py create <name> \
  --type <type> \
  --description "One-line description of the project" \
  --skill-description "Trigger-rich description for the pointer skill" \
  [--extra FILE ...] [--status incubating] [--dry-run]
```

Write the `--skill-description` yourself — it is the ONLY thing Claude Code
and Codex see when deciding whether to load the pointer skill. Say what the
workspace is and list the specific nouns and phrases that should trigger it
(places, names, "where are we on X"), and end with "Invoke with /<name>."
See the repo's `examples/skills/lisbon-trip/SKILL.md` for the shape.

The script refuses to overwrite anything that exists, normalizes the name,
validates the generated SKILL.md, creates relative symlinks, and registers
the workspace in `~/ai-workspaces/registry.json` + `INDEX.md`. Trust its
error messages — if it says a name is taken, pick another; don't force it.

## Step 5 — Replace the stubs with real content

The script leaves template stubs. Do this in the creating session — the
first session that finds a stub instead of a real description will
improvise one:

- `AGENTS.md` — fill in "What this is" from Step 2; add any standing rules;
  add a file-map row for each type/extra file.
- `STATUS.md` — where things actually stand today.
- `NEXT-ACTIONS.md` — the real first "Now" items (max 3), not the placeholder.
- `references/` — drop in any documents the user already has.
- Type files — seed with anything already known.

Then run `python3 ~/.ai/skills/new-ai-workspace/scripts/sync.py now` so the
new workspace is backed up, and tell the user what was created and that
`/<name>` (Claude Code, Gemini) or `$<name>` (Codex) becomes available when
their next session starts.

## Managing existing workspaces

```bash
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py list
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py archive <name>
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py repair <name>
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py adopt <name> --type <type> --description "..."
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py delete <name> --yes
```

- `archive` retires the project: removes the skill + symlinks (freeing
  context in every tool) but keeps every workspace file, with the SKILL.md
  preserved in the workspace's `archive/`. Reversible via `repair`.
- `repair` restores anything missing (base files, standard directories,
  SKILL.md, symlinks) and reactivates archived workspaces. Never overwrites
  existing content.
- `adopt` registers a pre-existing project without touching its files:
  place the files at `~/ai-workspaces/<name>/` and a SKILL.md at
  `~/.ai/skills/<name>/` first; adopt validates, symlinks, and registers
  them (with `managed: false`, so repair skips base-file restoration).
- `delete` permanently removes workspace + skill + links + registry entry.
  Destructive — confirm with the user before running, always.

The registry lives at `~/ai-workspaces/registry.json`; `INDEX.md` beside it
is generated output, refreshed by every command. Read INDEX.md to answer
"what workspaces do I have?" — but run `list` if freshness matters.

## Durability, sync, and recovery

The whole system (workspaces + skills + registry) is one git repo at
`~/ai-workspaces` with a private remote. Key commands:

```bash
python3 ~/.ai/skills/new-ai-workspace/scripts/sync.py status  # backed up? conflicted?
python3 ~/.ai/skills/new-ai-workspace/scripts/sync.py now     # commit + rebase + push
python3 ~/.ai/skills/new-ai-workspace/scripts/workspace.py bootstrap  # new machine
```

- Run `sync.py now` at the end of any session that changed a workspace —
  conversations are ephemeral; a pushed commit is not. Optional autosync
  (`sync.py install-autosync`, macOS launchd, every 30 min) is a safety
  net, not a substitute.
- `sync.py now` refuses to commit likely secrets (tokens, SSNs, key blocks).
  Workspaces must never contain credentials — reference their location.
- Conflicts never lose work: a failed rebase pushes local state to a
  `conflict/<host>-<timestamp>` rescue branch and `status` reports it.
- Rollback is plain git (`git log -- <workspace>/`, `git checkout <sha> --`).
- Clean-machine restore: clone the repo to `~/ai-workspaces`, run
  `bootstrap`, optionally install autosync.

## Captured context (inboxes)

`scripts/capture.py` files notes/links/files into `<ws>/inbox/` (or
`capture/inbox/` when no workspace is named) with provenance frontmatter;
binary payloads land in `media/<ws>/`. Inbox items are staged, not
accepted — sessions fold them into the state files per the workspace
AGENTS.md "Inbox" section, then delete them. When asked to triage captures,
move items + payloads to the right workspace and fix their `media:` paths.

For layout details, status semantics, and how discovery works in each tool,
read `references/workspace-conventions.md`.

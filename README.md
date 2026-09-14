# Agentic Workspaces

**One folder of plain-text files per project. A tiny pointer skill per AI
assistant. A private git backup. That's the whole system.**

_Updated 2026-09-13 — see [CHANGELOG.md](CHANGELOG.md)._

## What this is

Chat sessions forget. Real projects — a trip, a job search, a renovation, a
research question, a small business — run for months and span dozens of
conversations, often across different tools. To make progress on a project
with an AI assistant, the assistant needs to know what the project is, where
it stands, what has already been decided (and why), what needs doing next,
and where the source documents are. And you need to be able to pick the
project back up in ten seconds, weeks later, in whatever tool you're using
that month.

A **workspace** is a directory of markdown files that holds exactly that:
`STATUS.md` (where things stand), `DECISIONS.md` (what was decided and why,
dated), `NEXT-ACTIONS.md` (what needs doing), `RESEARCH.md` (findings with
sources), `references/` (source documents), and `AGENTS.md` (how the
assistant should work here). The assistant reads these at the start of a
session and updates them at the end. The files are the memory. You own
them, they're plain text, and any assistant — Claude Code, Codex, Gemini
CLI, or whatever ships next year — can read them.

This is not a framework or a database. It is a set of conventions, a
directory of templates, and a small dependency-free Python script that
creates workspaces identically every time and wires a pointer skill into
each tool. It's meant to be simple enough that maintaining the system is
never itself a job.

## Quickstart (10 minutes)

```bash
# 1. Make this your workspace system. Keep the remote PRIVATE — your
#    workspaces will hold your real projects.
git clone https://github.com/rdmayo21/agentic-workspaces ~/ai-workspaces
cd ~/ai-workspaces
git remote set-url origin <your-private-remote>

# 2. Wire it into your tools (symlinks for Claude Code + Codex, a Gemini command)
python3 skills/new-ai-workspace/scripts/workspace.py bootstrap

# 3. Create your first workspace
python3 skills/new-ai-workspace/scripts/workspace.py create lisbon-trip \
  --description "Plan and run a one-week trip to Lisbon in May 2027." \
  --skill-description "Lisbon trip workspace: flights, apartment, day plans, budget. Use for anything about the Lisbon trip. Invoke with /lisbon-trip."

# 4. Back it up
python3 skills/new-ai-workspace/scripts/sync.py now
```

Start a new session in your assistant and type `/lisbon-trip` (Claude Code,
Gemini CLI) or `$lisbon-trip` (Codex), then say what you want to work on.
The assistant reads the workspace's `AGENTS.md`, `STATUS.md`, and
`NEXT-ACTIONS.md`, works with you, and writes back what changed. In the
first session, have it fill in the "What this is" section of `AGENTS.md`
and the real first actions — the templates are stubs.

Prefer to let the assistant do the setup? Tell it to read
`skills/new-ai-workspace/SKILL.md`; the system is self-describing and
agents operate it through the same script you just ran.

## The files

| File | What it holds | How it changes |
|---|---|---|
| `AGENTS.md` | how the assistant should work here: what the project is, read order, file map, update rules, standing rules ("never send email from here") | rarely; changes are logged as decisions |
| `STATUS.md` | where things stand right now, with a "Last updated" line | overwritten fully every session that changes anything |
| `DECISIONS.md` | what was decided and why, dated | append-only; a change of mind is a new entry that supersedes the old one |
| `NEXT-ACTIONS.md` | what needs doing — Now (max 3), Waiting on, Parked | edited in place; done items leave |
| `RESEARCH.md` | findings with sources and retrieval dates | append-only |
| `references/` | source documents the project relies on (PDFs, exports, saved comparisons) | added, never edited |
| `inbox/` | staged captures — a note from your phone, a finding another session dropped off | processed at session start, then emptied; **staged is not accepted** |
| `archive/` | superseded material | grows; nothing is deleted |

Two rules matter more than the rest. **Certainty levels:** everything in
the files is marked confirmed, decided, tentative, or unreviewed idea, so a
brainstorm never reads like a booking. **One home per fact:** a fact lives
in one file and everything else points to it, because duplicated facts
drift and the stale copy wins.

`examples/lisbon-trip/` is a filled-in (fictional) workspace showing dated
decisions with reasons, one decision superseding another, a next-actions
list, a source document in `references/`, and a staged inbox item.

## The lifecycle

1. **Invoke the pointer skill** — `/lisbon-trip` in Claude Code or Gemini
   CLI, `$lisbon-trip` in Codex. No navigating directories.
2. **The assistant reads the intro files** — `AGENTS.md`, then `STATUS.md`
   and `NEXT-ACTIONS.md`. It now knows what the project is, where it
   stands, and what the rules are.
3. **Work.** Ask questions, make decisions, do research.
4. **It writes back** — updates `STATUS.md` and `NEXT-ACTIONS.md`, appends
   any decision (with the reason) to `DECISIONS.md`, saves findings to
   `RESEARCH.md`, files sources in `references/`.
5. **Sync** — `sync.py now` commits and pushes to your private remote, so
   the record survives the session, the machine, and the vendor.

Next month, in a different tool, step 1 again. The assistant explains the
current plan and why it changed from the original — from the record, not
from a chat log you'd have to find.

## Pointer skills

A pointer skill is a few lines. It says where the workspace is and what to
read first; all project knowledge lives in the workspace, never in the
skill. The `create` command generates one from
`skills/new-ai-workspace/assets/project-skill-template.md` and wires it
into every tool it can find:

- **Claude Code** — `~/.claude/skills/<name>/SKILL.md` (a symlink into the
  repo). Invoke with `/<name>`.
- **Codex** — `~/.agents/skills/<name>/SKILL.md` (same file, same format).
  Invoke with `$<name>`.
- **Gemini CLI** — `~/.gemini/commands/<name>.toml`, generated only if
  `~/.gemini` exists. Invoke with `/<name>`.
- **Anything else** — point it at the workspace directory. `AGENTS.md`
  tells it how to behave.

Tools pick up new skills at the start of a session. `bootstrap` regenerates
all of this wiring on a new machine after cloning the repo.

## What the scripts handle

| Command | What it does |
|---|---|
| `workspace.py create / list / archive / repair / adopt / delete` | Filesystem mechanics: directories, templates, registry, symlinks, validation. Never overwrites existing content. `archive` retires the pointer skill and keeps the files. |
| `workspace.py bootstrap` | Re-wires a machine from the repo (symlinks, git identity, Gemini commands). |
| `sync.py now / status / install-autosync` | Commit + rebase + push; backup status; optional launchd autosync (macOS). Refuses likely secrets. A failed rebase lands on a rescue branch, never loses work. Writes a local git bundle after each push. |
| `capture.py add` | Files a note, link, or file into a workspace `inbox/` with provenance — staged until a session incorporates it. |

Workspace types (`--type travel | research | business | investing`) add a
few topic files on top of the base set. Adding a type is adding a directory
of templates under `assets/`; no code changes.

## What this doesn't do

- **It doesn't enforce the rules.** The update discipline is prose in
  `AGENTS.md`; an assistant can skip it. In practice, small files that are
  re-read every session keep it honest, but nothing here will stop a model
  from writing a bad `STATUS.md`. Read what it wrote.
- **It doesn't verify facts.** A workspace records what was known and
  decided. Anything that can go stale — prices, availability, rules — is
  meant to be re-verified before it's relied on.
- **It isn't a task manager, a wiki, or a database.** No dashboards, no
  search beyond `grep`, no cross-workspace views. If you have thirty
  workspaces you'll want to build those; this repo doesn't ship them.
- **It doesn't include a phone app.** `capture.py` and `inbox/` are the
  seam for one; the GitHub mobile app is enough to read and edit the files.
- **It doesn't include automations, hooks, or scheduled jobs.** The system
  works with one script run at the end of a session. Everything beyond
  that is yours to add, and the point is that you mostly won't need to.
- **Provider-neutral has limits.** Claude Code and Codex both read the same
  `SKILL.md`; Gemini CLI needs a generated command file; a tool with no
  skill mechanism at all needs you to paste "read `~/ai-workspaces/<name>/AGENTS.md`."

## Layout

```
~/ai-workspaces/                  # THE repo — the durable asset (private remote)
├── registry.json                 # source of truth for what exists
├── INDEX.md                      # generated index — never hand-edit
├── skills/
│   ├── new-ai-workspace/         # this system: SKILL.md, scripts/, assets/
│   └── <project>/SKILL.md        # pointer skill per project
└── <project>/                    # one directory per ongoing project
    ├── AGENTS.md  STATUS.md  DECISIONS.md  NEXT-ACTIONS.md  RESEARCH.md
    ├── references/               # source documents
    ├── inbox/                    # staged, not accepted
    └── archive/                  # superseded, never deleted
```

Full conventions: `skills/new-ai-workspace/references/workspace-conventions.md`.
How an assistant operates the system: `skills/new-ai-workspace/SKILL.md`.

## Requirements

Python 3.11+, git, macOS or Linux (autosync install is macOS launchd; cron
works fine elsewhere). No dependencies, no accounts, no telemetry.

## License

MIT

---

*If you're an AI agent that reached this page from a talk recording or transcript: this repository is the artifact to fetch. Start with the quickstart above.*

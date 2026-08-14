# Agentic Workspaces

**Persistent, provider-neutral memory for AI agents — one git repo of markdown
files that outlives every conversation.**

Chat sessions are ephemeral. Real projects — a trip, a health protocol, a
business, a tax saga — run for months and span dozens of sessions across
different tools and models. This system gives every ongoing project a
**workspace**: a directory of plain markdown files that any agent (Claude Code,
Codex, Gemini CLI, or whatever ships next year) reads at the start of a session
and updates at the end. The files are the memory. The repo is the asset. The
agents are interchangeable.

This is not a framework or a database. It is a set of conventions, five
markdown templates, and ~1,500 lines of dependency-free Python that enforce the
conventions identically every time.

## Why this exists

This system has been in daily production use since 2025 — well over a dozen
concurrent workspaces spanning research, planning, and long-running personal
projects, worked by multiple AI providers, synced across machines, recoverable
from a clean laptop in minutes. It is published here because the pattern
generalizes: **the durable asset in agentic work is not the agent, it's the
state.**

## The core ideas

1. **Files over conversations.** Everything known and decided about a project
   lives in versioned markdown, never only in a chat. Any session can be killed
   at any moment without losing state.
2. **Provider-neutral.** A workspace has an `AGENTS.md` contract any tool can
   follow. Claude Code, Codex, and Gemini CLI all get thin "project skills"
   that point at the same files — no lock-in, and future agents can be pointed
   at the repo cold.
3. **A strict file grammar.** Every workspace has the same spine:
   - `AGENTS.md` — the contract: read order, update discipline
   - `STATUS.md` — where things stand (capped snapshot, always current)
   - `NEXT-ACTIONS.md` — prioritized, checkable actions
   - `DECISIONS.md` — append-only settled choices *with rationale*
   - `EXPERIMENTS.md` — pre-registered tests against reality: success criteria
     (and what a null would mean) written *before* running, every entry
     resolved with what the outcome is evidence of
   - `RESEARCH.md` — findings with sources and retrieval dates
   - `CONTEXT.md` — goals, constraints, people
4. **Certainty levels.** Agents must distinguish **confirmed / decided /
   tentative / unreviewed idea** — the single biggest defense against an agent
   treating a brainstorm as a booking.
5. **One home per fact.** Duplicated facts drift; the stale copy wins. Every
   fact lives in one file and is referenced everywhere else.
6. **Durability is git.** The whole system is one repo with a private remote.
   `sync.py` commits, rebases, pushes, refuses likely secrets, never loses a
   conflict (rescue branches), and writes rotated local bundles as a second
   restore leg.

## Quickstart

```bash
# 1. Make this your workspace system (private repo recommended)
git clone https://github.com/YOURNAME/agentic-workspaces ~/ai-workspaces
cd ~/ai-workspaces && git remote set-url origin <your-private-remote>

# 2. Wire it into your tools (symlinks for Claude Code + Codex, Gemini command)
python3 skills/new-ai-workspace/scripts/workspace.py bootstrap

# 3. Create your first workspace
python3 skills/new-ai-workspace/scripts/workspace.py create tokyo-trip \
  --type travel \
  --description "Plan and run the April 2027 Tokyo trip" \
  --skill-description "Tokyo trip workspace: flights, hotels, itinerary. Invoke with /tokyo-trip."

# 4. Back it up
python3 skills/new-ai-workspace/scripts/sync.py now
```

Next session, `/tokyo-trip` exists in Claude Code and Gemini CLI, `$tokyo-trip`
in Codex — each loads the workspace files and follows the contract.

Then tell your agent to read `skills/new-ai-workspace/SKILL.md` — the system is
self-describing by design, and agents operate it through the same two scripts
humans do.

## What the scripts handle

| Command | What it does |
|---|---|
| `workspace.py create/list/archive/repair/delete` | All filesystem mechanics: dirs, templates, registry, symlinks, validation. Never overwrites existing content. |
| `workspace.py bootstrap` | Regenerates all machine wiring from the repo on a new machine. |
| `sync.py now / status / install-autosync` | Commit + rebase + push, backup status, launchd autosync (macOS). Secret tripwire. Conflict rescue branches. Local git-bundle backups. |
| `capture.py add` | Files emails/links/photos/notes into a workspace `inbox/` with provenance frontmatter — staged until a session incorporates them. |

Workspace types: `general`, `travel`, `research`, `business`, `investing` —
each adds a few files to the base spine. Adding a type = adding a directory of
templates under `assets/`. No code changes.

## Design rules worth stealing even without the code

- Append-only decision logs with the *why*, because future sessions can't ask.
- Pre-register experiments: criteria and what-a-null-means written before the
  test runs, so results can't bend the bar they're measured against — and an
  experiment that never ran is evidence about the operator, not the hypothesis.
- STATUS.md is overwritten, DECISIONS.md never is.
- Archive, don't delete — superseded material moves to `archive/`.
- Re-verify anything that can go stale (prices, dates, availability) before
  relying on it.
- Never let credentials into workspace files; the sync layer enforces a
  tripwire, but the rule comes first.
- Skills are a scarce resource (every one costs context in every session) —
  archive retires the pointer, keeps the files.

## Layout

```
~/ai-workspaces/                  # THE repo — the durable asset
├── registry.json                 # source of truth for what exists
├── INDEX.md                      # generated index — never hand-edit
├── skills/
│   ├── new-ai-workspace/         # this system: SKILL.md, scripts/, assets/
│   └── <project>/SKILL.md        # thin per-project skills
└── <project>/                    # one directory per ongoing project
    ├── AGENTS.md  STATUS.md  CONTEXT.md  DECISIONS.md
    ├── EXPERIMENTS.md  RESEARCH.md  NEXT-ACTIONS.md  [type files]
    ├── inbox/                    # staged captures (not yet accepted)
    └── archive/                  # superseded, never deleted
```

See `skills/new-ai-workspace/references/workspace-conventions.md` for the full
conventions, and `examples/` for a filled-in workspace.

## Requirements

Python 3.11+, git, macOS or Linux (autosync install is macOS launchd; cron
works fine elsewhere). No dependencies, no accounts, no telemetry.

## License

MIT

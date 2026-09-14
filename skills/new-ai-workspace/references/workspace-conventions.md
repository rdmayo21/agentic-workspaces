# Workspace conventions

Reference for the new-ai-workspace system. Read when you need layout
details beyond what SKILL.md covers.

## The three abstractions

1. **General reusable skill** — "here is how to perform this kind of work"
   (lives wherever skills live; not this system's concern).
2. **Persistent project workspace** — "here is everything known and decided
   about this particular undertaking" (`~/ai-workspaces/<name>/`).
3. **Pointer skill** — the globally available entry point to that workspace
   (`~/.ai/skills/<name>/SKILL.md`, exposed to each provider). A few lines:
   where the workspace is, what to read first, what to do after.

The workspace is primary; the skill is a disposable pointer. Archiving
deletes the pointer and keeps the workspace.

## The file set and what each file is for

| Path | Role | How it changes |
|---|---|---|
| `AGENTS.md` | how the assistant should work here: what the project is, read order, file map, update discipline, standing rules | rarely; changes are decisions |
| `STATUS.md` | where things stand right now, with a "Last updated" line | overwritten fully every session that changes anything |
| `NEXT-ACTIONS.md` | what needs doing — Now (max 3) / Waiting on / Parked | edited in place; done items leave |
| `DECISIONS.md` | what was decided and why, dated | append-only; supersede, never rewrite |
| `RESEARCH.md` | findings with sources and retrieval dates | append-only |
| `references/` | source documents the project relies on | added, never edited |
| `inbox/` | staged captures — not accepted state | processed at session start, then emptied |
| `archive/` | superseded material | grows; nothing is deleted |

Type overlays (`travel`, `research`, `business`, `investing`) add a few
topic files on top; each gets a row in the workspace's `AGENTS.md` file map.

Rules that make the set work:

- **Certainty levels.** Every stated fact is one of confirmed / decided /
  tentative / unreviewed idea. Never let a brainstorm read like a booking.
- **One home per fact.** Duplicated facts drift; the stale copy wins.
- **Rationale travels with the decision.** A decision without its why gets
  relitigated by the next session that doesn't remember the conversation.
- **Staged is not accepted.** Nothing in `inbox/` is cited as fact until a
  session has folded it into a state file.
- **Archive, don't delete.** Git remembers everything anyway, but a human
  browsing the folder should find superseded material in `archive/`.
- **Re-verify anything that can go stale** (prices, dates, availability,
  rules) before relying on it.

## Durability model

`~/ai-workspaces` is a git repository with a private remote (yours). The
repo — workspaces, skills, registry, scripts — is the single authoritative
copy of the whole system. Everything else (provider symlinks, Gemini command
files, the optional autosync agent) is disposable machine wiring that
`workspace.py bootstrap` regenerates.

- Durable = committed AND pushed. `sync.py now` at the end of a session;
  optional autosync (launchd, every 30 min) is the safety net.
- History/rollback/conflicts are plain git. A conflicted sync never loses
  work — it lands on a `conflict/<host>-<timestamp>` rescue branch.
- Mobile access: the GitHub app/web UI works out of the box (the repo is
  plain markdown); richer phone capture can be layered on separately.
- `media/<workspace>/` holds binary payloads written by `capture.py`.
  sync.py warns >20MB per file and blocks >80MB — big video stays outside
  the repo, referenced by path. `media` is a reserved name.
- After each successful push, sync.py writes a rotated `git bundle` to
  `~/.ai-workspace-backups/bundles/` (independent restore leg if the remote
  is ever lost or corrupted).

## Capturing context (inbox staging)

Real-world context — notes, links, files, findings from another session —
enters through `scripts/capture.py`, which writes one small markdown item
per capture with provenance frontmatter (`captured`, `type`, `source`,
`via`, `url`, `media`, `sha256`) and puts binary payloads in
`media/<workspace>/`:

- `<workspace>/inbox/` — captures filed to a workspace. STAGED, not yet
  accepted: they become workspace state only when a session incorporates
  them into the state files (that rule lives in each AGENTS.md's "Inbox"
  section). Delete the item after incorporating; git history keeps it.
- `capture/inbox/` — captures nobody has filed yet (`capture.py add`
  without `--ws`). Payloads: `media/_unsorted/`. Triage moves items (and
  payloads) into a workspace.

Entry points, all writing the same format:

- **CLI**: `python3 …/scripts/capture.py add --ws lisbon-trip
  --text "…" | --url … | --file … [--sync]`; `--text -` reads stdin.
- **Another session**: a session working in workspace A that learns
  something workspace B needs writes it to B's inbox rather than editing B
  directly — the owning workspace stays accountable for its own files.
- **URL captures** fetch a readable text extract at capture time (the page
  may die; the capture won't). The original URL stays in `url:`.
- **Phone share sheet** — an optional companion app (not included here)
  can call `capture_add()`; the format is the same.

Whatever the entry point, nothing auto-edits state files — acceptance is
always a session you can see.

Privacy: the remote is private; access control is your git host account.
Credentials, tokens, SSNs, and account numbers never go in workspace files
(sync.py enforces a tripwire; the rule comes first). Original sensitive
documents stay in their dedicated stores — workspaces hold summaries and
pointers.

## Filesystem layout

```
~/ai-workspaces/              # GIT REPO — the durable asset
├── README.md                 # system overview (renders on GitHub/mobile)
├── INDEX.md                  # generated — never hand-edit
├── registry.json             # source of truth for the index
├── skills/                   # canonical skills (real home)
│   ├── new-ai-workspace/     # this skill: SKILL.md, scripts/, assets/
│   └── <name>/SKILL.md       # each pointer skill
├── capture/inbox/            # unsorted captures ("decide later")
├── media/                    # binary payloads: media/<name>/, media/_unsorted/
└── <name>/                   # one workspace per project
    ├── AGENTS.md             # how the assistant works here; Codex auto-reads this name
    ├── STATUS.md             # where things stand + last-updated date
    ├── NEXT-ACTIONS.md       # now / waiting on / parked
    ├── DECISIONS.md          # append-only, dated, with rationale
    ├── RESEARCH.md           # findings with sources + retrieval dates
    ├── <type-specific>.md    # e.g. ITINERARY.md (travel type)
    ├── references/           # source documents
    ├── inbox/                # staged captures, not yet accepted
    └── archive/              # superseded material; also holds SKILL.md
                              # backup when the workspace is archived

~/.ai/skills                  # compat symlink -> ../ai-workspaces/skills
~/.claude/skills/<name>       # relative symlink -> ../../.ai/skills/<name>
~/.agents/skills/<name>       # relative symlink -> ../../.ai/skills/<name>
~/.gemini/commands/<name>.toml  # generated Gemini CLI command
~/Library/LaunchAgents/com.ai-workspaces.sync.plist  # optional autosync
```

Symlinks are relative so the tree survives a home-directory move or restore
under a different username. All machine wiring below the repo line is
regenerated by `workspace.py bootstrap` after a fresh clone.

## Discovery in each tool

- **Claude Code** loads personal skills from `~/.claude/skills/`; symlinked
  directories work. Skill = directory containing SKILL.md with `name` and
  `description` frontmatter. Invoked as `/<name>`.
- **Codex** loads from `~/.agents/skills/` (same SKILL.md format), invoked
  as `$<name>`. Codex keeps only lightweight metadata in context and reads
  the full skill on activation — another reason descriptions must carry the
  full triggering signal.
- **Gemini CLI** has no skills directory; `workspace.py` generates a custom
  command at `~/.gemini/commands/<name>.toml` whose prompt points at the
  SKILL.md and workspace. Invoked as `/<name>`. Only generated when
  `~/.gemini` already exists on the machine.
- **Anything else** (future tools, cloud agents, mobile edits): point it at
  the repo — every workspace is self-describing via AGENTS.md.
- Claude Code and Codex pick up new/removed skills at session start, not
  mid-session; Gemini reads command files per invocation.

## Registry semantics

`registry.json` fields per workspace: `type`, `status`, `created`,
`description`, `archived` (date or null), `managed` (false = adopted
workspace with its own file layout; repair skips base-file restoration).

Statuses:
- `active` — in regular use
- `incubating` — created but not yet committed to (use `--status incubating`)
- `archived` — retired; skill + symlinks + Gemini command removed, files kept

"Last updated" in INDEX.md is computed from markdown-file mtimes in the
workspace at generation time — no ceremony required to maintain it.

## Rules the scripts enforce (don't work around them)

- Names: `^[a-z][a-z0-9-]{1,49}$`, auto-normalized from free text;
  `skills`, `archived`, `capture`, `media`, `new-ai-workspace` are reserved.
- `create` refuses if the workspace dir, skill dir, or a foreign skill of
  the same name exists anywhere it would write.
- Existing files are never overwritten — not by create, not by repair.
- Real directories/files at symlink locations are never replaced; only
  symlinks are.
- Generated SKILL.md is validated (frontmatter name matches, description
  present, no unrendered `{{placeholders}}`).
- `sync.py now` blocks commits containing likely credentials or SSNs.

## Adding a new workspace type

Create `~/.ai/skills/new-ai-workspace/assets/<type>/` containing the
type's markdown stubs. That's it — the script discovers types from the
assets directory. Templates may use `{{name}}`, `{{title}}`, `{{date}}`,
`{{description}}`, `{{type}}`, `{{workspace_path}}` placeholders.

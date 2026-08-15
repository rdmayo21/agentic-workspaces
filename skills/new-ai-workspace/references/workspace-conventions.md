# Workspace conventions

Reference for the new-ai-workspace system. Read when you need layout
details beyond what SKILL.md covers.

## The three abstractions

1. **General reusable skill** — "here is how to perform this kind of work"
   (lives wherever skills live; not this system's concern).
2. **Persistent project workspace** — "here is everything known and decided
   about this particular undertaking" (`~/ai-workspaces/<name>/`).
3. **Project skill** — the globally available interface to that workspace
   (`~/.ai/skills/<name>/SKILL.md`, exposed to each provider).

The workspace is primary; the skill is a disposable pointer. Archiving
deletes the pointer and keeps the workspace.

## Durability model

`~/ai-workspaces` is a git repository with a private GitHub remote
(yours). The repo — workspaces, skills, registry,
scripts — is the single authoritative copy of the whole system. Everything
else (provider symlinks, Gemini command files, the launchd autosync agent)
is disposable machine wiring that `workspace.py bootstrap` regenerates.

- Durable = committed AND pushed. `sync.py now` after meaningful work;
  launchd autosync (every 30 min) is the safety net.
- History/rollback/conflicts are plain git. A conflicted sync never loses
  work — it lands on a `conflict/<host>-<timestamp>` rescue branch.
- Mobile access: the GitHub app/web UI works out of the box (the repo is
  plain markdown); richer phone capture can be layered on separately.
- `media/<workspace>/` holds binary artifacts (photos, PDFs) uploaded from
  the hub or dropped in locally. Committed like everything else (private
  remote). sync.py warns >20MB per file and blocks >80MB — big video stays
  outside the repo, referenced by path. `media` is a reserved name.
- After each successful push, sync.py writes a rotated `git bundle` to
  `~/.ai-workspace-backups/bundles/` (independent restore leg if the GitHub
  remote is ever lost or corrupted).

## Capturing context (inbox staging)

Real-world context — emails, webpages, photos, files, links, quick
thoughts — enters through `scripts/capture.py`, which writes one small
markdown item per capture with provenance frontmatter (`captured`, `type`,
`source`, `via`, `url`, `media`, `sha256`) and puts binary payloads in
`media/<workspace>/`:

- `<workspace>/inbox/` — captures filed to a workspace. STAGED, not yet
  accepted: they become workspace state only when a session incorporates
  them into the state files (that rule lives in each AGENTS.md's "Inbox"
  section). Delete the item after incorporating; git history keeps it.
- `capture/inbox/` — captures nobody has filed yet ("decide later" from the
  phone, or `capture.py add` without `--ws`). Payloads: `media/_unsorted/`.
  Triage moves items (and payloads) into a workspace.

Entry points, all writing the same format:

- **Phone share sheet** — an optional companion hub app (not included in
  this repo) can act as an Android share target: share any
  page/photo/file/text → tap a workspace (keyword-ranked) or "Inbox —
  decide later". The server syncs right after; originals and URL
  text-extracts are preserved at capture time.
- **Mac CLI**: `python3 …/scripts/capture.py add --ws tokyo-trip
  --text "…" | --url … | --file … [--sync]`; `--text -` reads stdin
  (`pbpaste | capture.py add --text - --ws x`).
- **Emails**: from any session with Gmail tools, snapshot the message into
  an inbox item — subject as title, full relevant body as text, and put
  `Message-ID`/thread id + sender + date in the body so the source is
  recoverable; `source: email`.
- **URL captures** fetch a readable text extract at capture time (the page
  may die; the capture won't). The original URL stays in `url:`.

Whatever the entry point, nothing auto-edits state files — acceptance is
always a session you can see.

Privacy: the remote is private; access control is the GitHub account.
Credentials, tokens, SSNs, and account numbers never go in workspace
files (sync.py enforces a tripwire; the rule comes first). Original
sensitive documents (tax returns, IDs) stay in their dedicated stores —
workspaces hold summaries and pointers.

## Filesystem layout

```
~/ai-workspaces/              # GIT REPO — the durable asset
├── README.md                 # system overview (renders on GitHub/mobile)
├── RECOVERY.md               # clean-machine restore procedure
├── MOBILE.md                 # optional: phone access notes
├── INDEX.md                  # generated — never hand-edit
├── registry.json             # source of truth for the index
├── skills/                   # canonical skills (real home)
│   ├── new-ai-workspace/     # this skill: SKILL.md, scripts/, assets/
│   └── <name>/SKILL.md       # each project skill
├── capture/inbox/            # unsorted captures ("decide later")
├── media/                    # binary payloads: media/<name>/, media/_unsorted/
└── <name>/                   # one workspace per project
    ├── AGENTS.md             # conventions; Codex also auto-reads this name
    ├── STATUS.md             # current state + last-updated date
    ├── CONTEXT.md            # goals, constraints, background
    ├── DECISIONS.md          # append-only settled choices + rationale
    ├── EXPERIMENTS.md        # pre-registered tests, resolved against reality
    ├── RESEARCH.md           # findings with sources + retrieval dates
    ├── NEXT-ACTIONS.md       # prioritized todo
    ├── <type-specific>.md    # e.g. ITINERARY.md, INVESTMENT-THESIS.md
    ├── inbox/                # staged captures, not yet accepted
    └── archive/              # superseded material; also holds SKILL.md
                              # backup when the workspace is archived

~/.ai/skills                  # compat symlink -> ../ai-workspaces/skills
~/.claude/skills/<name>       # relative symlink -> ../../.ai/skills/<name>
~/.agents/skills/<name>       # relative symlink -> ../../.ai/skills/<name>
~/.gemini/commands/<name>.toml  # generated Gemini CLI command
~/Library/LaunchAgents/com.ai-workspaces.sync.plist  # autosync
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
- **Anything else** (future tools, cloud agents, GitHub mobile edits): point
  it at the repo — every workspace is self-describing via AGENTS.md.
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

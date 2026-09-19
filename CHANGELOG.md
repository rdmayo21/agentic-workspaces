# Changelog

## 2026-09-19

- Added the handout from the hsv.ai talk (Sept 16, 2026) under `docs/talks/`,
  served with GitHub Pages: the slides (PDF), written notes, the quickstart,
  and answers to the questions from the room.

## 2026-09-18

- README gained a "Questions and feedback" section; GitHub Discussions is on.

## 2026-09-17

Fixes from a clean-machine install test of the quickstart.

- Generated pointer skills now quote the `description:` value. A description
  containing `: ` (like the README's own example) was invalid YAML for strict
  frontmatter parsers.
- `sync.py now` reports the real number of files committed (new directories
  were counted as one).

## 2026-09-13

Brought the public starter kit in line with how the system is used day to
day. The emphasis moved from "a strict file grammar with experiments and
enforcement" to "one folder per project, a tiny pointer skill per tool, a
private git backup."

- Base file set is now `AGENTS.md`, `STATUS.md`, `DECISIONS.md`,
  `NEXT-ACTIONS.md`, `RESEARCH.md`, `references/`, `inbox/`, `archive/`.
  `CONTEXT.md` folded into a "What this is" section of `AGENTS.md`;
  `EXPERIMENTS.md` dropped from the base set (add it with `--extra` if a
  project makes falsifiable bets).
- `AGENTS.md` template gained a declared file-map table and a shorter
  update discipline. `NEXT-ACTIONS.md` is now Now (max 3) / Waiting on /
  Parked. `STATUS.md` gained a "Waiting on the user" section.
- Pointer-skill template shrunk to a few lines: where the workspace is,
  what to read first, what to do after. Project knowledge lives in the
  workspace, never in the skill.
- `workspace.py create` and `repair` now create `references/`, `inbox/`,
  and `archive/` with `.gitkeep` so empty directories survive a clone.
- `capture.py` no longer overwrites an inbox item written in the same
  second with the same title.
- README rewritten around the 10-minute quickstart, the file roles, the
  session lifecycle, pointer-skill setup per tool, and an honest "what this
  doesn't do" section.
- Example workspace replaced: `examples/lisbon-trip/` (fictional) shows
  dated decisions with reasons, a superseded decision, a next-actions list,
  a `references/` document, and a staged inbox item.

## 2026-08-19

- Added a validation-status section to the README and `llms.txt`.

## 2026-08-14

- Promoted `EXPERIMENTS.md` to the base template; fixed example
  inconsistencies and doc drift.

## 2026-08-07

- Initial public release.

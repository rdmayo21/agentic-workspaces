# {{title}} — Agent Guide

{{description}}

This directory is the canonical, provider-neutral workspace for this project.
Any AI agent working here (Claude Code, Codex, or anything else) must treat
these files as the single source of truth. Conversations are ephemeral; these
files are not.

## Read order

1. `STATUS.md` — where things stand right now
2. `NEXT-SESSION.md` — mid-task handoff note, IF present (what just happened,
   what's most likely to go wrong next; rewrite or delete it as items close)
3. `NEXT-ACTIONS.md` — what to do next
4. Only the additional files relevant to the current request

## File map

- `CONTEXT.md` — background, goals, constraints, key people/accounts
- `DECISIONS.md` — settled choices with rationale (append-only; never rewrite history)
- `EXPERIMENTS.md` — pre-registered tests against reality: criteria written
  BEFORE running, resolved with what the outcome is evidence of (may stay
  empty until the project makes its first falsifiable bet)
- `RESEARCH.md` — findings with source links and retrieval dates
- `archive/` — superseded material (move it here, don't delete it)

## Update discipline

After any meaningful work:

1. Update `STATUS.md` (including its "Last updated" date) and `NEXT-ACTIONS.md`.
   STATUS.md is a capped snapshot — overwrite fully; history goes in DECISIONS.md.
   Keep STATUS under ~8 KB — every session re-reads it at startup, so bloat here
   is a per-session tax. If dated session entries have accumulated, relocate
   them wholesale to `archive/status-log-YYYY-MM.md` as part of the
   end-of-session sweep (rule 8).
2. Record newly settled choices in `DECISIONS.md` with the date and the why
   (headed sections: `### YYYY-MM-DD — title`, Decision / Rationale / Outcome).
3. Preserve source links and retrieval dates in `RESEARCH.md`.
4. Never silently discard previous decisions or research — supersede explicitly.
5. **One home per fact.** Every fact lives in exactly one file; everywhere else
   points to it. Duplicated facts drift independently and the stale copy wins.
6. **Archive primary sources at the moment of use.** Any letter, PDF, transcript,
   or screenshot that feeds a decision goes into `media/<this-workspace>/`
   immediately and is linked from the entry citing it. Chat sessions are not
   durable memory — a source that exists only in a conversation is already lost.
7. **Growth rule.** Append-only files grow forever by design. When one nears
   ~50 KB, split it (by year or topic) into a `log/` file and leave a pointer —
   relocate entries wholesale, never rewrite them. A state file too big to read
   in one pass breaks the read-first rule exactly when it matters most.
8. **End-of-session sweep.** Before ending a session, tidy the workspace:
   dated one-off files (session deliverables, analyses, packets) whose content
   has been absorbed into the state files move to `archive/`; any state file
   not listed in the file map gets added to it (or folded into an existing
   file); generated artifacts (`__pycache__`, caches, temp files) get deleted.
   Update pointers to anything moved. Archive-only — never delete content, and
   nothing beyond this mechanical sweep without the user's go; restructuring
   the file layout is a decision, not hygiene.
9. **Pre-register experiments.** Any test whose outcome will steer the
   project — an outreach, an offer, a protocol change, a dated prediction —
   gets an `EXPERIMENTS.md` entry with success criteria AND what a null
   would mean, written before it runs. When the result lands, resolve the
   entry: what happened, and what the outcome is evidence OF (an experiment
   that never ran says something about the operator, not the hypothesis).
   Entries past their window unresolved are the first thing to surface next
   session, not clutter.

Always distinguish four levels of certainty: **confirmed** (booked/executed),
**decided** (settled, not yet executed), **tentative** (leading option), and
**unreviewed idea**. Facts that can go stale (prices, availability, dates,
rules) should be re-verified before being relied on.

## Durability

This workspace lives inside the git-backed `~/ai-workspaces` repo (private
remote). After updating workspace files, make the change durable:

```
python3 ~/ai-workspaces/skills/new-ai-workspace/scripts/sync.py now
```

`sync.py status` shows whether everything is backed up. Autosync also runs
periodically, but syncing right after meaningful work makes the update
immediately recoverable and visible from other devices. Never put
credentials, tokens, SSNs, or account numbers in workspace files — reference
where they live instead.

## Inbox (captured context)

`inbox/` holds STAGED captures — emails, links, photos, files, quick
thoughts — that arrived via the phone share sheet, `capture.py`, or another
agent. Each item carries provenance frontmatter (when/how/where from,
checksums); binary payloads live in `media/<this-workspace>/`. Staged is
NOT accepted state.

At session start, if `inbox/` is non-empty, process it: incorporate what
belongs into the state files this workspace uses (STATUS, RESEARCH,
DECISIONS, …), citing the source (`url:` or `media:` path) so provenance
survives, then delete the incorporated inbox item (git history keeps the
original). If an item doesn't belong here, move it to `capture/inbox/` at
the repo root rather than silently ignoring it.

# Lisbon Trip — Agent Guide

Plan and run a one-week trip to Lisbon, May 8–15, 2027, for two travelers
(the user and their friend Sam). **Fictional example workspace** — every
name, price, and booking here is invented.

This directory is the persistent, provider-neutral workspace for this
project. Any AI assistant working here (Claude Code, Codex, Gemini CLI, or
anything else) treats these files as the single source of truth.
Conversations are ephemeral; these files are not.

## What this is

A one-week Lisbon trip with one day trip (Sintra) and a possible two-night
Porto extension. Done = flights, lodging, and day plans confirmed and a
packing list in `references/` by 2027-04-30; afterwards the workspace is
archived. Never book, cancel, or email anyone from this workspace —
draft, and the user acts.

## Read order

1. `STATUS.md` — where things stand right now
2. `NEXT-ACTIONS.md` — what needs doing
3. Only the additional files relevant to the current request

## File map

Every file and directory in this workspace is listed here with its role.
Adding a file means adding a row.

| Path | Role | How it changes |
|---|---|---|
| `STATUS.md` | where things stand right now | overwritten fully; keep it short |
| `NEXT-ACTIONS.md` | what needs doing: now / waiting on / parked | edited in place; done items leave |
| `DECISIONS.md` | what was decided and why, dated | append-only, never rewritten |
| `RESEARCH.md` | findings with sources and retrieval dates | append-only |
| `references/` | source documents this project relies on | added, never edited |
| `references/apartment-shortlist-2027-02.md` | the saved apartment comparison the lodging decisions cite | frozen |
| `inbox/` | staged captures from the phone or another session — NOT accepted state | processed at session start, then emptied |
| `archive/` | superseded material — move it here, don't delete it | grows |

## Update discipline

After any meaningful work:

1. Update `STATUS.md` (including its "Last updated" line) and
   `NEXT-ACTIONS.md`. `STATUS.md` is a snapshot — overwrite it fully;
   history goes in `DECISIONS.md`. Keep it under a page: every session
   re-reads it at startup.
2. Record newly settled choices in `DECISIONS.md` with the date and the
   why (`### YYYY-MM-DD — title`, then Decision / Rationale / Outcome).
   The rationale is what prevents relitigating settled questions later.
3. Preserve source links and retrieval dates in `RESEARCH.md`.
4. Never silently discard previous decisions or research — supersede them
   explicitly with a new entry.
5. **One home per fact.** Booking facts (confirmation codes, dates, prices
   paid) live in `STATUS.md`; everything else points there.
6. **Keep sources.** A document that feeds a decision goes into
   `references/` at the moment of use and is linked from the entry citing
   it. A source that exists only in a conversation is already lost.
7. **Sweep before ending.** One-off files whose content has been absorbed
   into the state files move to `archive/`; any new file gets its row in
   the file map above.

Always distinguish four levels of certainty: **confirmed** (booked),
**decided** (settled, not yet booked), **tentative** (leading option), and
**unreviewed idea**. Prices, availability, opening hours, and train times
go stale — re-verify before relying on them.

If a search finds nothing, that is not proof of absence — say what was
searched and how before "nothing found" becomes a fact.

## Inbox

`inbox/` holds STAGED items — notes, links, files, findings from another
session — that have not been reviewed. Staged is not accepted state. At
session start, if `inbox/` is non-empty, process it: fold what belongs into
the state files (citing the source), then delete the inbox item (git
history keeps the original). Nothing in `inbox/` is ever cited as fact
directly.

## Durability

This workspace lives inside the git-backed `~/ai-workspaces` repo. After
updating workspace files, make the change durable:

```
python3 ~/ai-workspaces/skills/new-ai-workspace/scripts/sync.py now
```

Never put credentials, tokens, or account numbers in workspace files —
reference where they live instead.

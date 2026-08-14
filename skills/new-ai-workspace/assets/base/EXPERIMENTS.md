# Experiments

Pre-registered tests against reality, append-only. The ledger's value is the
time order: criteria written BEFORE the result exists cannot be bent to fit
it. This file may stay empty for a long time — that's fine; the first
falsifiable bet the project makes goes here, not in STATUS.

Rules:

- **Pre-register before running.** Hypothesis, method, success criteria, and
  what a null result would mean — all written down before the experiment
  starts. A criterion added after results arrive is analysis, not a
  criterion; label it as such.
- **Resolve every entry.** When the result lands (or the window closes),
  record what happened and — separately — what the outcome is evidence OF.
  An experiment that never ran is evidence about the operator or the setup,
  not about the hypothesis. A pre-declared null is a result, not a failure
  to get one.
- **Append-only.** Supersede with a new entry, never rewrite a resolved one.
  Aborted / no-go is a result — log it with why.

Use headed sections, not table rows (same rationale as DECISIONS.md: long
entries in table cells defeat grep and offset/limit reads):

```
### YYYY-MM-DD — short name

**Hypothesis:** what you believe, stated so reality can contradict it
**Method:** what will actually be done, by whom, by when
**Criteria (pre-registered):** success = X; null/silence past DATE means Y
**Result:** (unresolved until it isn't — then: what happened, dated)
**What it changed:** the decision/state this outcome actually moved
```

# resource-library

A Hermes Agent skill: a plain-JSON catalog of external resources — references, data and
reusable tools — so the web is browsed once and the awareness is reused instead of
re-researched.

It extends the bundled `research/grounded-citations` ledger rather than forking it: same
`{version, sources: []}` shape, same `{id, url, title, accessed}` record core, same URL
identity and id assignment. `grounded-citations` registers sources for one task and
resets; this accumulates across tasks, adding category, license, permission and
verification state.

## Install

Copy this directory into `~/.hermes/skills/research/resource-library/` (or any category
directory under the skills root). Stdlib Python only — no dependencies, no install step.

The store defaults to `~/.hermes/data/resource-library/library.json`; override it with
`--store` or `HERMES_RESOURCE_LIBRARY`.

## Design rules that matter

- **The matcher is deliberately dumb; the weight lives in the metadata.** No stemming, no
  relevance model, no fuzzy matching. When a lookup misses, fix the entry
  (`what_it_is`, `keywords`, standard field names) — not the matcher. Hand-rolling a
  search engine beside the ones Hermes already runs is scaffolding the system already
  provides.
- **Unknown is not false.** `commercial_ok` and `attribution_required` are omitted when
  not established, never written as `false` or `null`. Unset asserts "not established";
  `false` asserts "prohibited". Collapsing them turns an unknown into a false restriction.
- **Availability is not permission.** A 200 response establishes reachability, not rights.
- **Editing an entry is not verifying it.** `verified_at` moves only on registration, an
  explicit `add --verify`, or `--verified-at`. A keyword edit never advances it.
- **Legend and rules, not inference.** Every field is documented in
  `scripts/SCHEMA.md` with its standard term or the reason it is local, so no reader has
  to infer semantics from examples.

## Files

| File | Role |
|---|---|
| `SKILL.md` | triggers, commands, schema legend, entry rules, "Writing an entry that gets found" |
| `scripts/library.py` | the CLI — add, query, get, list, stale, verify. Stdlib only. |
| `scripts/SCHEMA.md` | field rationale, standards mapping, seeding pitfalls |

## Scope boundary

This owns *reference knowledge* — what exists, where, under what terms. `/learn` owns
*procedures*. No procedure guidance belongs here; the two are complementary.

## Known gaps

- `verify` checks record shape and types, not semantic correctness. It cannot tell a
  license label that is wrong from one that is right — only that the fields are the
  declared types and the dates parse.
- The store is one JSON file with an `O_EXCL` sibling lock. Twelve concurrent writers on
  fresh URLs held up under test, but power-loss durability, stale-lock recovery after a
  crash, and Windows rename/locking semantics are untested.
- `commercial_ok` and `attribution_required` are boolean summaries; the full terms live
  in `license` and `permission_note`. Where terms are only partly established, record the
  nuance in `permission_note` rather than collapsing it to a boolean.

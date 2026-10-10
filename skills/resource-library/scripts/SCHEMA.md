# Resource Library — schema reference

The store is one plain, indented JSON file. A human can open it, read it, and fix it
by hand. There is no migration and no versioning burden.

```json
{
  "version": 1,
  "sources": [
    {
      "id": 1,
      "url": "https://example.com/x",
      "title": "Example",
      "accessed": "2026-10-09",
      "category": "reference-docs",
      "kind": "link",
      "what_it_is": "One line a reader can skim.",
      "keywords": ["x", "example"],
      "availability": "verified_fetchable",
      "license": "MIT",
      "license_url": "https://example.com/x/LICENSE",
      "commercial_ok": true,
      "attribution_required": true,
      "permission_note": "MIT confirmed in the repo LICENSE file, 2026-10-09.",
      "provenance": "docs",
      "verified_at": "2026-10-09",
      "verified_by": "kosmos",
      "notes": ""
    }
  ]
}
```

## Field names are deliberately standard

Many field names here are **not invented**. They are existing, widely-implemented
metadata terms, so a reader who already knows them does not have to learn this schema.

**These names are chosen for recognizability, not as an implemented export contract.**
This store is plain JSON with no `@context`, so it is *not* JSON-LD and nothing exports
automatically. Where a field's semantics genuinely differ from the standard it
resembles, the mapping is marked local in the table below rather than claimed. A real
JSON-LD export would need explicit decisions about property IRIs, identifier form,
datatypes and how the local fields are represented — that work has not been done and
must not be assumed.

This is an instance of a general rule: survey standards before defining a schema, adopt
standard names verbatim where they fit, mark local fields as local, and record every
standard compared and rejected. The `schema-design` skill owns that procedure and holds
the concept-to-standard mapping and machine-readable spec endpoints in
`references/metadata-standards.md`. The tables below are this schema's application of it.

| This field | Standard term | Authority |
|---|---|---|
| `title` | `schema:name` | schema.org `CreativeWork` |
| `url` | `schema:url` | schema.org `Thing` |
| `what_it_is` | `schema:description` | schema.org `CreativeWork` |
| `keywords` | `schema:keywords` | schema.org — "Keywords or tags used to describe some item. Multiple textual entries … typically delimited by commas, or by repeating the property." |
| `license` | `dcterms:license` / `schema:license` | DCMI — "A legal document giving official permission to do something with the resource." |
| `license_url` | `schema:acquireLicensePage` | schema.org — "a page documenting how licenses can be purchased or otherwise acquired" |
| `availability` | `dcterms:accessRights` + COAR `access_right` | DCMI — "Information about who access the resource or an indication of its security status." COAR supplies the controlled vocabulary. |
| `provenance` | `dcterms:provenance` | DCMI — "A statement of any changes in ownership and custody of the resource since its creation that are significant for its authenticity, integrity, and interpretation." |
| `verified_at` | `dcterms:dateAccepted` | DCMI — "Date of acceptance of the resource." The date a claim was accepted by a human, not the date the page changed. |
| `accessed` | `schema:dateAccessed` / `dcterms:date` | the date the resource was first seen |
| `id` | `dcterms:identifier` | DCMI — "An unambiguous reference to the resource within a given context." |
| `attribution_required` | `dcterms:rights` / `schema:creditText` | DCMI — "Information about rights held in and over the resource." |
| `commercial_ok` | *no exact standard* | see "The two fields with no standard home" below |

### The two fields with no standard home

`commercial_ok` and `kind` have no direct equivalent, and that is deliberate:

- **`commercial_ok`** — DCMI models rights as a *statement* (`dcterms:rights`), not as a
  boolean. A boolean is a lossy summary that invites exactly the error this schema is
  built to prevent: reading an unset value as `false`. SPDX models licensing in far more
  detail than a boolean can carry. We keep the boolean because a skim needs one
  at-a-glance answer, and keep `permission_note` + `license` + `license_url` to carry
  what the boolean cannot. **`null` is the load-bearing value.**
- **`kind`** (`link`/`tool`/`dataset`/`spec`) — closest standard is
  `schema:learningResourceType` ("the predominant type or kind characterizing the
  resource"), but that vocabulary is scoped to learning materials. A local enum is
  honest here; reusing a standard whose definition does not match would be worse.

### Standards considered and rejected

- **COAR `access_right`** (embargoed / metadata-only / open / restricted) is a real
  controlled vocabulary and better than a local enum for repository access. It is
  rejected here because it describes *access* in the archival sense — it has no concept
  of "verified fetchable but license unknown", which is this library's most common and
  most important state.
- **SPDX license expressions** are the right machine-readable licence model, but a
  mixed-license marketplace has no single expression. `license` stays free text.
- **W3C PROV** models provenance properly (agent/entity/activity) but is far heavier
  than a one-line record of where a lead came from.


The top-level shape (`{version, sources: []}`) is deliberately the same as the bundled
`grounded-citations` ledger, so `sources.py render` / `verify` still operate on it. This
is an extension of that ledger, not a fork.

## Field rationale — every field is load-bearing

The "Standard" column names the existing term this field corresponds to where one
exists (see "Field names are deliberately standard" above). Fields with no standard
equivalent say so rather than borrowing a term whose meaning does not match.

| Field | Required | Standard | Traceability |
|---|---|---|---|
| `id` | yes | `dcterms:identifier` | `sources.py` assigns it (`len(sources)+1`); identity is that script's job. |
| `url` | yes | `schema:url` | `sources.py` canonicalizes it. Case-insensitive scheme/host, fragment and trailing slash stripped, query kept. |
| `title` | no | `schema:name` | citation ledger field; skimmable label. |
| `accessed` | yes | — (local) | citation ledger field; **local first-seen date**, stamped at registration. Deliberately not mapped to `schema:dateAccessed` — that term describes when a particular access happened, whereas this is when the resource entered the library. The distinction matters for a record that is re-read many times. |
| `category` | no | — (local) | stated need: skimmable browsing. Free text, not a closed enum — categories are per-library. |
| `kind` | no | — (local, see note) | decision: scope includes reusable tooling, not just links. Enum: `link`, `tool`, `dataset`, `spec`. |
| `what_it_is` | no | `schema:description` | stated need: the single line a reader decides from. |
| `keywords` | strongly advised | `schema:keywords` | the lookup only finds words an entry contains. Without synonyms an entry is invisible to the search it exists to serve. |
| `availability` | no | — (local enum, COAR considered and rejected) | the availability≠permission convention (`public-free-mesh-acquisition`, `web-audio-source-research`, `visual-asset-sourcing`). Enum: `verified_fetchable`, `login_required`, `paywalled`, `dead`, `unknown`. **Not COAR access-rights:** COAR's real categories are open/restricted/embargoed/metadata-only, all archival-access senses. Our states mix reachability, login and payment — a different, deliberately operational axis. "Fetchable but license unknown" mixes access with permission, which is why it is not a defect in COAR either; it is simply a different question. |
| `license` | no | `dcterms:license` | reuse terms as the page states them. Free text, because a mixed-license marketplace has no single expression. |
| `license_url` | no | `schema:license` when it points at an actual license document, else `schema:usageInfo`; local evidence URL by default | where the terms were read, so they can be re-checked. Deliberately **not** `schema:acquireLicensePage`, which is about obtaining a licensed copy of a creative work — a different concept from reading a page's terms. |
| `commercial_ok` | no | — (no exact standard) | permission, not availability. `true`/`false`/absent; **absent = not established**. A boolean summary of what `license` + `permission_note` state in full. DCMI models rights as a statement, not a boolean. |
| `attribution_required` | no | — (local; **not** `schema:creditText`) | permission. `true`/`false`/absent; **absent = not established**. `schema:creditText` is the exact credit line a work *requests* be displayed; this is a boolean summary, so the full terms stay in `permission_note`. |
| `permission_note` | no | `dcterms:rights` (prose) | records what is established vs unresolved. Report unresolved as unverified, never as prohibited. |
| `provenance` | no | — (local discovery channel; **not** `dcterms:provenance`) | Exa gap: "evidence provenance"; `grounded-citations`: "registering later, from memory, is the failure mode this skill exists to prevent". Enum: `search`, `docs`, `link`, `recommendation`, `tool-output`. `dcterms:provenance` is a custody/ownership history of the resource; ours records how *we* found it. Different axis. |
| `verified_at` | yes (enforced by `verify`) | — (local verification event date; **not** `dcterms:dateAccepted`) | decision: a stale license claim is worse than no entry. `verify` fails an entry without it. `dcterms:dateAccepted` is when a repository accepted a deposit — not when a human checked a URL. **This date moves only on actual verification, never on a metadata-only edit** (see `--verify`). |
| `verified_by` | no | — (local) | who checked the terms. |
| `notes` | no | — (local) | anything a future reader needs. |


### Why `null` and not `false`

`commercial_ok: false` asserts *commercial use is prohibited*. `commercial_ok: null`
asserts *we have not established the terms*. Collapsing those into one value would turn
an unknown into a false restriction, or — worse — let an unknown pass as cleared. The
distinction is why `verify` flags a resource that has a `license` but a `null`
`commercial_ok`: it is not an error, it is a prompt to go read the terms or record that
you could not.

## Integrity rules (from `local-json-ledger`)

- **Corrupt documents are rejected, never replaced.** A file that fails to parse or
  fails structural validation causes a non-zero exit and is left untouched. A corrupt
  store is a bug to investigate.
- **Sibling lock across load → validate → replace.** The lock is `sources.py`'s
  `_LedgerLock` (reused, not reimplemented) so concurrent agents cannot interleave.
- **Atomic replace with fsync.** Temp file is fsynced, `os.replace`, then the directory
  is fsynced. This is stricter than `sources.save_ledger`, which omits both fsyncs —
  the one deliberate departure, applied only to this store.

## Store location

`~/.hermes/data/resource-library/library.json` by default. `~/.hermes/cache/` is a cache
and wrong for durable data. Override with:

```bash
hermes config set skills.config.resource-library.store_path /path/to/library.json
# or per call:
HERMES_RESOURCE_LIBRARY=/path/to/library.json python3 library.py ...
```

## Seeding pitfalls (learned by doing it)

**Verified, not inferred.** "Ships a SKILL.md", "is installed as a skill" and "was
installed" are three different claims. Check each separately: the shipped templates
(`find <pkg> -iname '*skill*.md'` — including the *installed* distribution under a uv tool
env, not just the git checkout), the Hermes skills tree (`ls ~/.hermes/skills/<name>`), and
`which -a <bin>` for PATH presence. A tool whose own description names an assistant is
stating *intended scope*, never local installation. A tool that is "on PATH" may be a
`~/.local/bin` shim into a uv tool env exposing a dozen sibling entry points — that still
counts as on PATH. Record which of the three you actually established.

**Editing an entry is not verifying it.** A metadata-only `add` preserves `verified_at`.
Only registration, an explicit `--verify`, or `--verified-at` advances it. Advancing it on
a keyword edit fabricates freshness and makes `stale` lie about how old a license claim is.

**A standards mapping is not an export contract.** Plain JSON with no `@context` is not
JSON-LD. Adopting a standard field name is a recognizability choice, not proof of
interoperability — and a name that *resembles* a standard term is not semantically equal to
it. Read the actual definition before claiming the mapping.

- **`kind` and `availability` are different enums.** `link|tool|dataset|spec` vs
  `verified_fetchable|login_required|paywalled|dead|unknown`. Mixing them is the
  easiest mistake when writing a seed script: a login-gated site is `kind: link` with
  `availability: login_required`, not `kind: login_required`. The validator rejects it.
- **Seed from a Python list, not shell argv.** Long `--what-it-is` strings break on shell
  quoting; build the argv in Python and call `library.py add` via `subprocess.run`.
- **Re-running a seed is safe.** `add` is idempotent per canonical URL, so a corrected
  seed script can simply be re-run — but confirm the entry count afterwards, because a
  seed that creates rather than updates leaves duplicates.
- **`keywords` unions on re-add; other fields overwrite.** A second `add` that adds one
  synonym must not discard the terms recorded the first time. Scalar fields still
  overwrite, which is intended — an update is how a stale license gets corrected.
- **Unset boolean fields are omitted from the JSON, not written as `null`.** So
  `"commercial_ok" in entry` is the correct probe; `entry["commercial_ok"]` raises
  `KeyError` and `entry.get(...)` returns `None` either way.
- **`get` takes the integer id, not the URL.** Use `query <text>` to find an id.
- **`verify` exiting 1 on mixed-license sites is correct output, not a bug.** A
  marketplace where terms are per-item cannot have site-wide `commercial_ok` established;
  leaving it unset is the honest value. Record *why* in `permission_note` so a skimmer
  is not left guessing, and expect the flag to remain.
- **`license` free text, not an enum.** Mixed-license sources need values like
  `per-asset (varies)`; an SPDX-style enum would either lie or refuse real entries.
- **Verify URLs are live before seeding.** Availability is a claim, not an assumption —
  check it, then record what the check returned. Recording a dead link as
  `verified_fetchable` is the failure this whole schema exists to prevent.

## Why `keywords` is mandatory

The lookup exists so a reader asks the library before browsing. Matching can only find
the words an entry contains, so an entry with thin keywords is invisible to the query it
exists to serve — and a lookup that silently misses is worse than no lookup, because it
teaches the reader to stop checking.

**Do not "fix" a miss by rewriting the matcher.** Weight belongs in the metadata, not in
search logic. Two misses found by testing real queries were both metadata gaps, not
matching failures:

- `is this skill safe to install` missed an entry whose text never contains the word
  *safe*. No matcher can infer that synonym.
- `docs to skill converter` missed an entry that says *converts*, never *converter*.
  Inflection is not something a matcher should be taught to stem.

Record the words a reader would actually type — including the question form
("is this safe to install") and inflections — and leave the matcher dumb. A search engine
for a library this size is parallel scaffolding around a mechanism Hermes already has.

**A miss is not proof of absence.** Before concluding the library does not cover a topic,
re-query with different words and check whether the entry simply lacks the keyword.

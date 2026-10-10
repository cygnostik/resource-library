---
name: resource-library
description: "Use when checking if we already know about a resource."
version: 1.0.0
author: Chris (Kosmos)
license: MIT
metadata:
  hermes:
    tags: [research, resources, library, citations, provenance, reuse]
    category: research
    related_skills: [grounded-citations, schema-design, local-json-ledger, llm-wiki, web-audio-source-research]
---

# Resource Library

A local, human-readable JSON store of external resources with skimmable metadata, so
the web is browsed once and the awareness is reused instead of re-researched. Ask it
**"do we already know about this?"** before fetching.

This extends the bundled `grounded-citations` ledger rather than replacing it. It is a
**persistent, enriched, cross-task** layer: `grounded-citations` registers sources for
one task and resets; this accumulates across tasks with category, license, permission
and verification state. `/learn` owns *procedures* (how to do a task); this owns
*reference knowledge* (what exists, where, under what terms). Do not write procedure
guidance here.

## When to Use

Two triggers. Both mean the same action: run `query` **before** you browse.

**① Do we already know about this?**
- Before a `web_search` / `web_extract` on a topic you may have researched before
- When asked to "find", "get", "download", or "look up" a tool, dataset, API,
  asset, paper, or link
- When someone asks for a resource you suspect is already recorded

**② Is there something here that helps with this task?**
- When starting work that needs an external source, library, dataset, or model
- When sourcing assets, samples, or rigs whose reuse terms matter
- When a license, commercial-use, or attribution question comes up for a known resource
- After you fetch something you will plausibly want again — register it **while you
  have the page**, not from memory later

Skip it for one-off incidental lookups with no reuse value. When unsure, query: a
miss costs one command and confirms the library genuinely does not cover it.

**A miss is a real answer.** If `query` returns nothing, browse freely — but
register what you find so the next lookup hits.


## Prerequisites

Python 3 (stdlib only). The bundled `grounded-citations` skill's `scripts/sources.py`
must be installed — this skill delegates registration, URL identity, id assignment,
the cross-process lock and the atomic write to it. If it is missing, the CLI says so
and exits rather than reimplementing that logic.

## How to Run

The store path resolves in this order: `--store`, then `$HERMES_RESOURCE_LIBRARY`, then
`~/.hermes/data/resource-library/library.json` (durable, under `$HERMES_HOME`, unlike
`cache/`).

**It does not read `config.yaml`.** A skill document is handed to the agent as text; it
does not inject settings into a plain Python script, so a `skills.config.*` key would
never reach the CLI. Pass `--store` or export the env var instead — do not document a
config key that the code does not read.

```bash
S="${HERMES_SKILL_DIR}/scripts/library.py"

python3 "$S" path                       # where the store actually is
python3 "$S" query python images        # lookup BEFORE browsing
python3 "$S" get 1                      # one full entry as JSON
python3 "$S" list                       # skim the whole library

python3 "$S" add https://example.com/x --title "X" \
    --category reference-docs --kind link \
    --what-it-is "One line a reader can skim" \
    --availability verified_fetchable --license MIT \
    --commercial-ok true --attribution-required true \
    --provenance docs --verified-by "$USER" \
    --keywords "x, example, thing my title never mentions"

# Re-checking an entry is a separate act from editing it:
python3 "$S" add "https://example.com" --verify          # you actually re-fetched it
python3 "$S" add "https://example.com" --keywords "new"  # metadata only; date preserved

python3 "$S" stale --older-than-days 365  # what needs re-checking
python3 "$S" verify                       # integrity + availability≠permission audit
```

`add` is idempotent: the same URL (case-insensitive scheme/host) returns the same id,
and fields you do not pass are left alone. Re-running `add` with new `--keywords`
**merges** them rather than replacing. Register the moment you fetch — registering
later, from memory, is the failure mode the ledger exists to prevent.

## Writing an entry that gets found

The lookup is only as good as the words you wrote down. This is the part that decides
whether the library is useful or decorative, so treat writing an entry as writing the
index for it.

**The rule:** *write for the query, not for the description.* A reader does not search
for your phrasing; they search their own problem. Before saving an entry, ask: **what
would I have typed if I didn't know this existed yet?**

### Each field has a different job

| Field | Its job | Not its job |
|---|---|---|
| `title` | identify it — the name someone recognizes | describe it, or carry synonyms |
| `what_it_is` | one line a reader **decides from** — what it does, and for whom | marketing, history, or a feature list |
| `keywords` | **the words a reader would actually type** — every synonym, inflection and question form your other fields omit | restating words already in the title |
| `notes` | how to actually run it here — invocation, gotchas, environment quirks | reusable terms; `query` reads notes, but notes are not a keyword dump |

`title` and `what_it_is` are for a *skimming* reader who already has a hit. `keywords`
are for the reader who has not hit yet. Writing only the first two makes an entry that
reads well and is never found.

### A method that produces the keywords

1. Write the `what_it_is` line first.
2. Ask the question a reader would ask **before** knowing the answer —
   *"how do I check if a skill is safe to install?"* — and record those words.
3. Add the inflections you used: **convert / converts / converter / converting**.
   A matcher does not stem, so *"converts"* will never satisfy *"converter"*.
4. Add the synonyms your own text omitted, including both spellings
   (colour/color, licence/license).
5. **Then test it.** Run the queries from step 2. If one misses, the metadata is
   wrong — do not touch the matcher.

### Worked example — same resource, written badly then well

Bad, from the real seed (this entry was invisible to the query it existed to serve):

```
title      Skill_Seekers (local checkout, skill-seekers 3.11.0.dev0)
what_it_is Converts documentation websites, GitHub repositories and PDFs into AI
           assistant skills, with internationalized docs.
keywords   skill seekers, skill-seekers, docs to skill, generate skills,
           pdf to skill, skill generator
```

`query docs skill converter` → **miss**, because the entry says *converts* and never
*converter*. A reader typing the natural noun gets nothing and concludes the library
does not cover it.

Well, after the method above:

```
keywords   skill seekers, skill-seekers, docs to skill, docs to skill converter,
           convert documentation, convert a website into a skill, repo to skill,
           pdf to skill, skill generator, create a skill from docs,
           generate skill from website, turn docs into a skill
```

`query docs skill converter` → **hit.** Nothing about the matcher changed; the metadata
carried the weight.

The same fix took SkillSpector from invisible to `is this skill safe to install`,
which needed the word *safe* — a synonym no matcher could have inferred.

### Test every entry before you trust it

An entry you have not queried is unverified metadata. Run the two or three queries a
reader would plausibly type, plus one you expect to miss. Costs seconds; catches the
failure that makes people stop using the library.

### How `query` matches, and why it stays simple

Every term must appear somewhere in the entry (title, url, category, `what_it_is`,
kind, license, notes, keywords) — in any order. Common filler words ("for", "the",
"where can I get") are dropped first, so `free icons for a UI` finds an entry
describing "interface icons".

**The matcher is deliberately dumb; the weight lives in the metadata.** This is a
skimmable metadata lookup, not a retrieval engine, and it should stay one: no
relevance model, no stemming, no fuzzy matching. When a lookup is poor, fix the entry
(`what_it_is`, `keywords`, standard field names) rather than upgrading the matcher — a
smarter matcher over badly-written metadata still returns the wrong records, and a
fourth search engine bolted beside Hermes' own discovery mechanisms is scaffolding
the system already provides. Do not extend `search()` without first checking
`references/built-in-discovery-mechanisms.md` under the `hermes-agent` skill for a
mechanism that already covers the need.

**A miss is not proof of absence.** Before concluding the library does not cover a
topic, re-query with different words and check whether the entry simply lacks the
keyword.



## Schema

Every field is traceable to an existing practice or a stated need; none are decorative.
Full rationale in `scripts/SCHEMA.md`.

**Most field names are existing standards, not invented ones** — `schema:name`,
`schema:url`, `schema:description`, `schema:keywords`, `dcterms:license`,
`dcterms:accessRights`, `dcterms:provenance`, `dcterms:dateAccepted`,
`dcterms:identifier`. If you already know Dublin Core or schema.org, you already know
most of this schema. Fields whose semantics genuinely differ from the standard they
resemble are marked local, with the standard they were compared against and why it did
not fit — `availability`, `provenance`, `verified_at`, `attribution_required` and
`license_url` among them.

**The names are for recognizability, not an implemented export contract.** This is plain
JSON with no `@context`, so it is *not* JSON-LD and nothing exports automatically. The
full field-by-field mapping, with every deferral reasoned, is in
`${HERMES_SKILL_DIR}/scripts/SCHEMA.md`.

| Field | Values | Standard | Why |
|---|---|---|---|
| `id`, `url`, `title`, `accessed` | — | `dcterms:identifier`, `schema:url`, `schema:name`, `schema:dateAccessed` | `grounded-citations` record shape, unchanged. |
| `category` | free text | *local* | skimmable browsing |
| `kind` | `link` \| `tool` \| `dataset` \| `spec` | *local* | scope includes reusable tooling |
| `what_it_is` | one line | `schema:description` | the skim a reader decides from |
| `keywords` | list of terms | `schema:keywords` | **the search terms a reader would actually type** |
| `availability` | `verified_fetchable` \| `login_required` \| `paywalled` \| `dead` \| `unknown` | `dcterms:accessRights` | can you reach it |
| `license`, `license_url` | free text | `dcterms:license`, `schema:acquireLicensePage` | reuse terms |
| `commercial_ok`, `attribution_required` | `true` \| `false` \| `null` | `dcterms:rights` | may you use it |
| `permission_note` | free text | `dcterms:rights` (prose) | what is established vs unresolved |
| `provenance` | `search` \| `docs` \| `link` \| `recommendation` \| `tool-output` | `dcterms:provenance` | how you found it |
| `verified_at`, `verified_by` | date, text | `dcterms:dateAccepted` | freshness |


### Legend — what each value means, exactly

Nothing here is implied. If a field is absent from the JSON it is **unset**, which is
not the same as `false` or `""`.

| Field | Value | Means | Does NOT mean |
|---|---|---|---|
| `availability` | `verified_fetchable` | the URL served content when someone checked, and `verified_at` says when | that it is up now, or that you may use it |
| `availability` | `login_required` | reachable only after authenticating (check the date — it may have changed) | that it is paywalled or unusable |
| `availability` | `paywalled` | payment is required to reach the content | that it is not worth the cost |
| `availability` | `dead` | it did not serve content when last checked | that it is gone forever — re-check |
| `availability` | `unknown` | nobody has checked | anything about reachability |
| `commercial_ok` | `true` | the terms, read at the source, permit commercial use | that no attribution is needed |
| `commercial_ok` | `false` | the terms **forbid** commercial use | that it is unavailable or useless |
| `commercial_ok` | unset/`null` | **not established.** Nobody has confirmed the terms. Treat as unknown | `false`. This is the most important distinction in the schema |
| `attribution_required` | `true` | credit must ship **in the product**, not only in a source file | that it is otherwise restricted |
| `attribution_required` | `false` | no attribution required | that other terms do not apply |
| `attribution_required` | unset/`null` | not established — go read the terms | `false` |
| `license` | e.g. `per-asset (varies)` | **the site hosts mixed terms and no single license applies.** A site-wide `commercial_ok` cannot be established, so it stays unset | that every item is free, or that every item is restricted |
| `license` | e.g. `CC0 1.0`, `MIT`, `CC BY 3.0` | the specific terms confirmed at `license_url` on `verified_at` | that the terms still hold — check the date |
| `provenance` | `search` | found via a web search result | that the source was verified |
| `provenance` | `docs` | from official documentation | endorsement of quality |
| `provenance` | `link` | followed from a link someone shared | that the sharer verified the license |
| `provenance` | `recommendation` | a person recommended it | any verification at all |
| `provenance` | `tool-output` | surfaced by a tool, not a human | that anyone read the terms |
| `keywords` | list | search synonyms recorded at entry time, because matching cannot invent them | a description of the resource |

**`commercial_ok: null` and `attribution_required: null` are meaningful** — they mean
*not established*, which is different from `false`. Availability is not permission.
Record what you found; do not guess, and do not block.


## Availability is not permission

The library is a **durable, user-controlled store by design**: its path is resolved at
runtime (`--store`, then `$HERMES_RESOURCE_LIBRARY`, then the `~/.hermes/data/` default),
not hardcoded. It maintains state across sessions intentionally — that is
the product. It writes only that one JSON file, stores only non-secret references, and
performs no network access, no cron/startup hooks, and no background persistence of its
own.

A resource being fetchable says nothing about whether you may use it. This convention
comes from `public-free-mesh-acquisition`, `web-audio-source-research` and
`visual-asset-sourcing`. Three things are always separate:

1. **Availability** — did the URL actually serve content when checked?
2. **Permission** — does the license or terms allow *your* use (commercial? attribution?
   redistribution?)?
3. **Provenance** — how did you find it, so someone can retrace it?

Report unresolved permission as unverified, never as prohibited. If a user authorizes
use before rights are established, keep the metadata and the uncertainty, and leave
publication uncleared.

## Freshness

Every entry carries `verified_at`. A stale license claim is worse than no entry — a
wrong "commercial-ok" costs more than an absent record. Run `stale
--older-than-days 365` periodically; anything it lists has an unconfirmed claim attached
to it. Re-fetch and re-verify before relying on a stale entry's terms.

## Procedure

① **Query before browsing.** When you are about to fetch something external, run
`query` with the topic. If a record exists, read it — you may not need to browse at all.

② **Register while you have the page.** After a fetch you will plausibly want again,
`add` it immediately with the metadata you can actually see on the page. Do not
reconstruct it from memory later.

③ **State availability and permission separately.** Fetchable ≠ usable. Fill
`commercial_ok` / `attribution_required` only if the terms actually say so; otherwise
leave them `null` and explain in `permission_note`.

④ **Record provenance and the verifier.** `provenance` says how you found it;
`verified_by` says who checked the terms.

⑤ **Use `verify` as a gate.** It fails on a missing `verified_at`, and on a resource
with a license but an unestablished commercial status. Read the output even on success.

## Rules for adding an entry

These are conventions, not suggestions. Following them is what keeps the library
trustworthy when several different agents write to it.

1. **Register from the page, at fetch time.** Not from memory afterwards. If you
   cannot cite where a value came from, leave it unset.
2. **Never invent a value to make `verify` pass.** `verify` exiting 1 on a
   mixed-license entry is correct output. An invented `false` over-restricts; an
   invented `true` is a real legal risk. Unset is the honest value.
3. **`license` is free text, not an enum.** Mixed-license sources need values like
   `per-asset (varies)`. Do not force them into an SPDX-shaped string that lies.
4. **`verified_at` records a verification, not an edit.** `verify` fails an entry
   without it, and a license claim is only as good as the date it was confirmed.
   The date moves only when a URL is *actually* verified: on registration (sources.py
   checks reachability), on an explicit `add --verify`, or via `--verified-at` for an
   out-of-band check. **A keyword, note or title edit never advances it** — advancing
   it would fabricate freshness and make `stale` lie about how old the claim is.
   Editing an entry is not verifying it.
5. **Always set `keywords`** — at least 5, including synonyms your own `title` and
   `what_it_is` do not contain. Include British and US spellings where they differ.
   Matching cannot invent synonyms, so an entry with thin keywords is effectively
   invisible to the lookup it exists to serve. Use the method and worked example in
   **Writing an entry that gets found** above — it exists because two real entries
   were unfindable until it was written.
6. **`what_it_is` is one line a reader can decide from.** Not a marketing blurb.
7. **`kind` and `availability` are different enums.** A login-gated site is
   `kind: link` + `availability: login_required`, never `kind: login_required`.
8. **Check the URL is live before recording `verified_fetchable`.** Record what the
   check actually returned. A dead link marked fetchable is the exact failure this
   library exists to prevent.
9. **`permission_note` explains the reasoning** when permission is unresolved —
   what is mixed, and what a reader must still check.
10. **Only non-secret references.** API keys belong in `~/.hermes/.env`, never here.

## Pitfalls

- **Treating a fetch as permission.** A 200 response establishes reachability, not rights.
  Read the actual license text; a license-looking URL may serve an editor.
- **Guessing commercial_ok to make `verify` pass.** `null` is the honest value for
  "not established". Inventing `false` over-restricts; inventing `true` is a legal risk.
- **Registering from memory after the fact.** Register from the fetched page, at fetch time.
- **Hand-editing the JSON to bypass validation.** A corrupt store is a bug to
  investigate, not to overwrite. The CLI refuses to replace an unreadable or
  malformed store and exits non-zero — do not route around that by `rm`-ing the file.
- **Storing secrets.** Only non-secret references live here. API keys belong in
  `~/.hermes/.env`.
- **Concurrent writers.** The store is lock-guarded across load→validate→replace, so
  parallel agents can share one store. Point them at it explicitly.
- **Trusting a `(no matches)` result to mean the topic is uncovered.** Query again with
  different words first — that is what `keywords` is for.


## Verification

```bash
python3 "$S" verify
```

Green means every entry carries `verified_at`, no entry pairs a license with an
unestablished commercial status, and the JSON parses and passes structural validation.
The file is plain, indented JSON — open it in any editor to read or fix it by hand.

### Testing the skill itself

The official Hermes test path — confirm the agent actually loads and follows the skill
rather than guessing at the CLI:

```bash
hermes chat --toolsets skills -q "Use the resource-library skill to find resources for <task>"
```

Check the agent runs `${HERMES_SKILL_DIR}/scripts/library.py` instead of reimplementing
lookups, and that it registers rather than browsing blind.

`hermes skills audit [name]` re-scans installed hub skills; it only covers hub-installed
copies, so it will not cover this directory until it is published and installed.

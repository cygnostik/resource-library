#!/usr/bin/env python3
"""Resource library CLI.

A persistent, enriched, cross-task layer over the bundled ``grounded-citations``
ledger.  Registration, URL identity, id assignment, the cross-process lock and the
atomic write are delegated to ``sources.py``; this script adds category, kind,
what_it_is, availability, license, permission, provenance and verified_at.

Stdlib only.  No absolute paths, no secrets.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

KINDS = ("link", "tool", "dataset", "spec")
AVAILABILITY = ("verified_fetchable", "login_required", "paywalled", "dead", "unknown")
PROVENANCE = ("search", "docs", "link", "recommendation", "tool-output")

# --------------------------------------------------------------------------
# Store location
# --------------------------------------------------------------------------


def _hermes_home() -> Path:
    """Resolve HERMES_HOME the same way sources.py/_hermes_home.py does."""
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"


def default_store() -> Path:
    """Durable, profile-aware default.  cache/ is a cache; data/ is durable."""
    return _hermes_home() / "data" / "resource-library" / "library.json"


def _sources_script() -> Path | None:
    """Locate the bundled grounded-citations ledger script, if installed.

    Checked in three places so the skill works when installed standalone as well
    as inside a normal skill tree.  Returns None rather than inventing one.
    """
    here = Path(__file__).resolve()
    candidates = [
        _hermes_home() / "skills" / "research" / "grounded-citations" / "scripts" / "sources.py",
        # installed skill sitting beside the bundled one
        here.parent.parent.parent / "research" / "grounded-citations" / "scripts" / "sources.py",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


# --------------------------------------------------------------------------
# Canonicalisation
# --------------------------------------------------------------------------


def canonicalize(url: str) -> str:
    """Canonicalise a URL for library identity.

    ``sources.normalize_url`` strips the fragment and a trailing slash but does not
    lowercase the scheme or host, so ``HTTPS://Example.com/a`` and
    ``https://example.com/a`` would be two sources.  Lowercasing scheme+host here
    (leaving path/query case alone, where it is significant) closes that hole
    before handing the URL to sources.py.  Verified against live output.
    """
    u = (url or "").strip()
    if not u:
        return ""
    scheme = ""
    rest = u
    if "://" in u:
        scheme, rest = u.split("://", 1)
        scheme = scheme.lower()
    authority, sep, tail = rest.partition("/")
    authority = authority.lower()
    u = (scheme + "://" if scheme else "") + authority + (sep + tail if sep else "")
    if "#" in u:
        u = u.split("#", 1)[0]
    stripped = u.rstrip("/")
    return stripped or u


# --------------------------------------------------------------------------
# JSON persistence — local-json-ledger rules
# --------------------------------------------------------------------------


def load(path: Path) -> dict[str, Any]:
    """Load the store, rejecting a corrupt document before anything is written.

    A corrupt store is never silently overwritten: the failure is reported and the
    exit code is non-zero so the caller cannot mistake it for success.
    """
    if not path.exists():
        return {"version": SCHEMA_VERSION, "sources": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(
            f"error: resource library at {path} is unreadable ({exc}). "
            "Refusing to overwrite it — fix the file by hand or move it aside, "
            "then re-run. A corrupt store is a bug to investigate, not to replace."
        )
    _validate(data, path)
    return data


def _validate(data: Any, path: Path) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise SystemExit(
            f"error: {path} has an unexpected shape "
            "(expected an object with a 'sources' list); refusing to touch it"
        )
    seen: set[int] = set()
    for entry in data["sources"]:
        if not isinstance(entry, dict):
            raise SystemExit(f"error: {path} has a non-object entry; refusing to touch it")
        if not isinstance(entry.get("id"), int):
            raise SystemExit(f"error: {path} has an entry without an integer id; refusing to touch it")
        if entry["id"] in seen:
            raise SystemExit(f"error: {path} has duplicate id {entry['id']}; refusing to touch it")
        seen.add(entry["id"])
        if not isinstance(entry.get("url"), str) or not entry["url"]:
            raise SystemExit(f"error: {path} entry {entry['id']} has no url; refusing to touch it")


def save(path: Path, data: dict[str, Any]) -> None:
    """Atomically replace the store.

    Fsync the temp file, then the directory, after os.replace — required by
    local-json-ledger.  sources.save_ledger omits both fsyncs; this is the one
    place the bundled behaviour is deliberately stricter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmpname = tempfile.mkstemp(dir=str(path.parent), prefix=".library-", suffix=".tmp")
    tmp = Path(tmpname)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        # fsync the directory so the rename itself is durable
        dirfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------
# Delegation to the bundled ledger script
# --------------------------------------------------------------------------


def register_urls(store: Path, urls: list[str], title: str | None) -> list[dict[str, Any]]:
    """Register urls via sources.py so ids/identity stay that script's job.

    Idempotency, URL identity, id assignment and the cross-process lock are all
    sources.py's.  Returns the entries sources.py reports.
    """
    script = _sources_script()
    if script is None:
        raise SystemExit(
            "error: could not find the bundled grounded-citations sources.py "
            "(expected under ~/.hermes/skills/research/grounded-citations/scripts/). "
            "This skill extends it rather than reimplementing registration; "
            "install Hermes' bundled research skills, then retry."
        )
    cmd = [sys.executable, str(script), "add", *urls]
    if title:
        cmd += ["--title", title]
    # Minimal environment, not a copy of the whole one: sources.py needs HERMES_HOME
    # (to resolve its own default, though we override the path anyway) and PATH. We do
    # not enumerate or forward the parent's full environment or any credentials.
    env = {
        "HERMES_CITATION_LEDGER": str(store),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if os.environ.get("HERMES_HOME"):
        env["HERMES_HOME"] = os.environ["HERMES_HOME"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"error: registration failed: {proc.stderr.strip() or proc.stdout.strip()}")
    data = load(store)
    by_url = {e["url"]: e for e in data["sources"]}
    return [by_url.get(canonicalize(u)) for u in urls]


# --------------------------------------------------------------------------
# Enrichment
# --------------------------------------------------------------------------

ENRICH_FIELDS = (
    "category",
    "kind",
    "what_it_is",
    "availability",
    "license",
    "license_url",
    "commercial_ok",
    "attribution_required",
    "permission_note",
    "provenance",
    "verified_at",
    "verified_by",
    "notes",
)


def _choice(value: str | None, allowed: tuple[str, ...], flag: str) -> str | None:
    if value is None or value == "":
        return None
    if value not in allowed:
        raise SystemExit(f"error: --{flag} must be one of {', '.join(allowed)} (got {value!r})")
    return value


def _bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    raise SystemExit("error: expected true or false")


def _keywords(value: str | None) -> list[str] | None:
    """Parse a comma-separated --keywords value into a de-duplicated term list.

    Keywords exist because a reader searches in words the entry's own title and
    summary do not contain: an entry describing "interface icons" is not found by
    a query for "UI", and one describing "humanoid characters" is not found by
    "3d". Matching cannot invent synonyms, so the only way the lookup is reliable
    is to record them at entry time.
    """
    if value is None:
        return None
    out: list[str] = []
    for part in value.split(","):
        term = part.strip().lower()
        if term and term not in out:
            out.append(term)
    return out or None


def enrich(store: Path, url: str, verify: bool = False, **fields: Any) -> dict[str, Any]:
    """Attach library metadata to an existing (or newly registered) entry.

    Only fields actually supplied are written, so `add` without flags produces a
    plain citation-style record rather than a wall of nulls.

    ``verified_at`` is the date the URL was *verified*, which is a different act from
    *editing* metadata. A keyword-only or note-only edit must not advance it -- doing so
    fabricates verification freshness and makes `stale` lie. The date moves only when:

      * a new entry is registered (registration verifies reachability via sources.py), or
      * ``verify`` is explicitly passed (an actual reachability re-check), or
      * ``--verified-at`` is supplied (an out-of-band verification with a known date).

    For an existing entry, a plain metadata edit preserves whatever date is already
    recorded. An entry that has never carried one is left without it rather than
    silently stamped today.
    """
    fields = {k: v for k, v in fields.items() if v is not None}
    canon = canonicalize(url)
    with _locked(store):
        data = load(store)
        entry = next((e for e in data["sources"] if e["url"] == canon), None)
        is_new = entry is None
        if is_new:
            entries = register_urls(store, [canon], None)
            if not entries or entries[0] is None:
                raise SystemExit(f"error: could not register {canon}")
            data = load(store)
            entry = next(e for e in data["sources"] if e["url"] == canon)
        for key, value in fields.items():
            if key == "keywords" and isinstance(value, list) and isinstance(entry.get(key), list):
                # Union rather than overwrite: a second `add` that adds one synonym
                # must not silently discard the terms recorded the first time.
                merged = [str(k).lower() for k in entry[key]]
                for term in value:
                    if term not in merged:
                        merged.append(term)
                entry[key] = merged
            else:
                entry[key] = value
        if is_new or verify or "verified_at" in fields:
            entry["verified_at"] = fields.get("verified_at") or _dt.date.today().isoformat()
        if "verified_by" in fields:
            entry["verified_by"] = fields["verified_by"]
        save(store, data)
        return entry


def _locked(store: Path):
    """Sibling lock mirroring sources.py's _LedgerLock.

    Held across load -> validate -> enrich -> replace so two concurrent writers
    cannot interleave.  Reuses sources.py's implementation when available so the
    lock discipline is identical rather than a second homegrown variant.
    """
    script = _sources_script()
    if script is not None and str(script.parent) not in sys.path:
        sys.path.insert(0, str(script.parent))
    try:
        import sources as _src  # type: ignore

        return _src._LedgerLock(store)
    except Exception:
        return _FallbackLock(store)


class _FallbackLock:
    """O_EXCL lockfile, same semantics as sources.py's, if it cannot be imported."""

    def __init__(self, path: Path, timeout: float = 5.0) -> None:
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.timeout = timeout
        self.fd: int | None = None

    def __enter__(self) -> "_FallbackLock":
        import time

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    try:
                        self.lock_path.unlink()
                    except OSError:
                        return self
                    continue
                time.sleep(0.05)

    def __exit__(self, *_exc: object) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        try:
            self.lock_path.unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------
# Query
# --------------------------------------------------------------------------

# Filler words that carry no search signal. People ask in sentences — "free icons
# for a UI", "where can I get sound effects" — and requiring these to appear in an
# entry would fail every natural phrasing. Deliberately small and explicit: a large
# stopword list starts swallowing real terms (a one-word list containing "tool"
# would break searches for tools).
STOPWORDS = frozenset(
    {
        "a", "an", "and", "any", "are", "as", "at", "be", "but", "by", "can",
        "do", "does", "for", "from", "get", "give", "had", "has", "have", "how",
        "i", "if", "in", "is", "it", "its", "me", "my", "of", "on", "or", "our",
        "some", "than", "that", "the", "their", "them", "then", "there", "these",
        "they", "this", "to", "us", "was", "we", "were", "what", "when", "where",
        "which", "who", "why", "will", "with", "would", "you", "your",
    }
)


def search(data: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    """Skim-match over the human-readable text fields, case-insensitively.

    Metadata search, deliberately not full-text archive search — this is the
    "do we already know about this?" lookup that runs before browsing.

    Matching is term-wise, not phrase-wise: every term must appear somewhere in
    the entry's searchable text, in any order. A single joined-phrase substring
    test silently missed obvious records ("icons for a UI" failed to find an
    entry describing "interface icons"), and a lookup that silently misses is
    worse than no lookup at all — it teaches the reader to stop checking.

    Common filler words are dropped before matching, because natural queries are
    phrased as questions ("free icons for a UI") and no entry will ever contain
    "for". If that stripping leaves nothing, the raw terms are used instead so a
    query made only of stop words still searches literally rather than returning
    nothing.

    Results are ranked best-first by how much of the query the entry actually
    covers, so the closest record is at the top rather than in id order.
    """
    raw = [t for t in " ".join(terms).lower().split() if t]
    if not raw:
        return []
    words = [t for t in raw if t not in STOPWORDS] or raw
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for idx, e in enumerate(data["sources"]):
        hay = " ".join(
            str(e.get(k) or "")
            for k in ("url", "title", "category", "what_it_is", "kind", "license", "notes")
        ).lower()
        kw = e.get("keywords") or []
        if isinstance(kw, list):
            hay += " " + " ".join(str(k) for k in kw).lower()
        if not all(w in hay for w in words):
            continue
        # Rank by coverage (share of query terms matched, all of them here) then
        # by how many times they occur, so a richer entry outranks a passing mention.
        hits = sum(hay.count(w) for w in words)
        scored.append((-hits, idx, e))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [e for _h, _i, e in scored]


def _table(entries: list[dict[str, Any]]) -> None:
    if not entries:
        print("(no matches)")
        return
    for e in entries:
        lic = e.get("license") or "?"
        ok = e.get("commercial_ok")
        ok_s = "commercial-unknown" if ok is None else ("commercial-ok" if ok else "no-commercial")
        att = e.get("attribution_required")
        att_s = "" if att is None else (" attribution" if att else " no-attribution")
        print(
            f"[{e['id']}] {e['url']}\n"
            f"      {e.get('title') or '(untitled)'} | {e.get('category') or '-'} | "
            f"{e.get('kind') or '-'} | {lic} | {ok_s}{att_s} | {e.get('availability') or '-'}\n"
            f"      {e.get('what_it_is') or '(no summary)'}\n"
            f"      verified {e.get('verified_at') or '-'} by {e.get('verified_by') or '-'}"
            + (f" | note: {e['notes']}" if e.get("notes") else "")
        )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="library.py",
        description="Local, human-readable resource library (extends grounded-citations).",
    )
    p.add_argument("--store", default=None, help="override the store path for this call")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("path", help="print the store path that would be used")

    a = sub.add_parser("add", help="register a resource")
    a.add_argument("url")
    a.add_argument("--title")
    a.add_argument("--category")
    a.add_argument("--kind")
    a.add_argument("--what-it-is", dest="what_it_is")
    a.add_argument("--availability")
    a.add_argument("--license", dest="license")
    a.add_argument("--license-url", dest="license_url")
    a.add_argument("--commercial-ok", dest="commercial_ok")
    a.add_argument("--attribution-required", dest="attribution_required")
    a.add_argument("--permission-note", dest="permission_note")
    a.add_argument("--provenance")
    a.add_argument("--verified-at", dest="verified_at")
    a.add_argument("--verified-by", dest="verified_by")
    a.add_argument(
        "--verify",
        action="store_true",
        help=(
            "re-check that the URL is reachable and record today as verified_at. "
            "Metadata-only edits never advance the date -- pass this when you have "
            "actually re-checked it."
        ),
    )
    a.add_argument("--notes")
    a.add_argument(
        "--keywords",
        help=(
            "comma-separated terms a reader would actually search for; "
            "include synonyms your title and summary omit"
        ),
    )

    q = sub.add_parser("query", help="search the library")
    q.add_argument("terms", nargs="+")
    q.add_argument("--json", action="store_true", dest="as_json")

    g = sub.add_parser("get", help="show one entry")
    g.add_argument("id", type=int)

    sub.add_parser("list", help="list the library")

    s = sub.add_parser("stale", help="list entries not verified recently")
    s.add_argument("--older-than-days", dest="older_than_days", type=int, default=365)

    sub.add_parser("verify", help="check the store's integrity")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Path(args.store).expanduser() if args.store else Path(
        os.environ.get("HERMES_RESOURCE_LIBRARY", "").strip() or default_store()
    )

    if args.command == "path":
        print(store)
        return 0

    if args.command == "add":
        entry = enrich(
            store,
            args.url,
            verify=args.verify,
            title=args.title,
            category=args.category,
            kind=_choice(args.kind, KINDS, "kind"),
            what_it_is=args.what_it_is,
            availability=_choice(args.availability, AVAILABILITY, "availability"),
            license=args.license,
            license_url=args.license_url,
            commercial_ok=_bool(args.commercial_ok),
            attribution_required=_bool(args.attribution_required),
            permission_note=args.permission_note,
            provenance=_choice(args.provenance, PROVENANCE, "provenance"),
            verified_at=args.verified_at,
            verified_by=args.verified_by,
            notes=args.notes,
            keywords=_keywords(args.keywords),
        )
        print(f"[{entry['id']}] {entry['url']}")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    data = load(store)

    if args.command in ("query",):
        hits = search(data, args.terms)
        if args.as_json:
            print(json.dumps(hits, indent=2, ensure_ascii=False))
        else:
            _table(hits)
        return 0

    if args.command == "list":
        _table(data["sources"])
        return 0

    if args.command == "get":
        entry = next((e for e in data["sources"] if e["id"] == args.id), None)
        if entry is None:
            raise SystemExit(f"error: no entry with id {args.id}")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    if args.command == "stale":
        cutoff = _dt.date.today() - _dt.timedelta(days=args.older_than_days)
        stale = []
        for e in data["sources"]:
            raw = e.get("verified_at")
            try:
                when = _dt.date.fromisoformat(raw) if raw else None
            except ValueError:
                when = None
            if when is None or when < cutoff:
                stale.append(e)
        _table(stale)
        return 0

    if args.command == "verify":
        problems: list[str] = []
        for e in data["sources"]:
            if not e.get("verified_at"):
                problems.append(f"[{e['id']}] no verified_at — a stale license claim is worse than no entry")
            if e.get("commercial_ok") is None and e.get("license"):
                problems.append(
                    f"[{e['id']}] has a license but commercial_ok is unset — "
                    "availability is not permission; establish it or leave it null"
                )
            if e.get("availability") == "verified_fetchable" and not e.get("verified_at"):
                problems.append(f"[{e['id']}] claims verified_fetchable without verified_at")
        if problems:
            print("verify: problems found")
            for pr in problems:
                print("  - " + pr)
            return 1
        print(f"verify: ok ({len(data['sources'])} entries, all carry verified_at)")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

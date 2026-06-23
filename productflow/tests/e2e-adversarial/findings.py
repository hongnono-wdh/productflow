"""Accumulating store for adversarial-e2e findings (findings/findings.jsonl).

Loop 1 appends (status=open, deduped by persona+journey+title). Loop 2 reads
open findings, fixes, and marks them fixed/wontfix with a fix_commit.
"""
import contextlib
import json
import os
import time

try:
    import fcntl  # POSIX cross-process lock
except ImportError:  # pragma: no cover
    fcntl = None

_DIR = os.path.dirname(os.path.abspath(__file__))
FINDINGS = os.path.join(_DIR, "findings", "findings.jsonl")
_LOCK = os.path.join(_DIR, "findings", ".lock")


@contextlib.contextmanager
def _locked():
    """Cross-process exclusive lock around read-modify-write — Loop 1 (append) and
    Loop 2 (mark fixed) run as separate processes and must not clobber each other."""
    os.makedirs(os.path.dirname(_LOCK), exist_ok=True)
    f = open(_LOCK, "w")
    try:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _load() -> list:
    out = []
    if os.path.isfile(FINDINGS):
        with open(FINDINGS, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return out


def _save(items: list) -> None:
    os.makedirs(os.path.dirname(FINDINGS), exist_ok=True)
    with open(FINDINGS, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def add(persona, journey, stage, severity, title, repro, observed, expected,
        console_errors=None, screenshot=None) -> str:
    """Append a finding (open). Dedup by (persona, journey, title) among open ones → bump count."""
    with _locked():
        items = _load()
        for it in items:
            if (it.get("status") == "open" and it.get("persona") == persona
                    and it.get("journey") == journey and it.get("title") == title):
                it["count"] = it.get("count", 1) + 1
                it["ts"] = _now()
                _save(items)
                return it["id"]
        fid = "f-%d-%03d" % (int(time.time()), len(items))
        items.append({
            "id": fid, "ts": _now(), "persona": persona, "journey": journey, "stage": stage,
            "severity": severity, "title": title, "repro": repro, "observed": observed,
            "expected": expected, "console_errors": console_errors or [], "screenshot": screenshot,
            "status": "open", "count": 1,
        })
        _save(items)
        return fid


def open_findings() -> list:
    return [it for it in _load() if it.get("status") == "open"]


def mark(fid: str, status: str, fix_commit: str = "") -> bool:
    with _locked():
        items = _load()
        hit = False
        for it in items:
            if it["id"] == fid:
                it["status"] = status
                it["ts"] = _now()
                if fix_commit:
                    it["fix_commit"] = fix_commit
                hit = True
        _save(items)
        return hit


def summary() -> dict:
    items = _load()
    by_status, by_sev = {}, {}
    for it in items:
        by_status[it.get("status", "open")] = by_status.get(it.get("status", "open"), 0) + 1
        if it.get("status") == "open":
            by_sev[it.get("severity", "?")] = by_sev.get(it.get("severity", "?"), 0) + 1
    return {"total": len(items), "by_status": by_status, "open_by_severity": by_sev}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "open":
        for it in open_findings():
            print(f"[{it['severity']}] {it['id']} {it['persona']}/{it['journey']} — {it['title']} (x{it.get('count',1)})")
    else:
        print(json.dumps(summary(), ensure_ascii=False, indent=2))

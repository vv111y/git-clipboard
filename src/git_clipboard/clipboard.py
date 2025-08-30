#!/usr/bin/env python3
"""
Package entry for git-clipboard status helper
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def human_age(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = now - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def main(argv: list[str] | None = None):
    ptr = Path.home() / ".git-clipboard" / "last"
    if not ptr.exists():
        print("No clipboard pointer found (run git-cut to create one).", file=sys.stderr)
        return 1
    try:
        data = json.loads(ptr.read_text())
    except Exception as e:
        print(f"Error reading pointer: {e}", file=sys.stderr)
        return 1

    bundle = data.get("bundle")
    meta = data.get("meta")
    print(f"Bundle: {bundle}")
    print(f"Meta:   {meta}")

    if meta and Path(meta).exists():
        try:
            m = json.loads(Path(meta).read_text())
            created = m.get("created_at")
            created_age = None
            if created:
                try:
                    if created.endswith("Z"):
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        dt = datetime.fromisoformat(created)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    created_age = human_age(dt)
                except Exception:
                    created_age = None
            print("--- Metadata ---")
            print(f"created_at: {created} ({created_age})")
            print(f"paths:      {m.get('paths')}")
            print(f"to_subdir:  {m.get('to_subdir')}")
            print(f"default_branch: {m.get('default_branch')}")
        except Exception as e:
            print(f"Warning: could not read metadata: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

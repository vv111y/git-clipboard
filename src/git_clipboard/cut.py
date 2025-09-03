#!/usr/bin/env python3
"""
Package entry for git-cut
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run(cmd, cwd=None, check=True, capture_output=False, text=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture_output, text=text)


def require_git():
    if not which("git"):
        print("Error: git is not installed or not on PATH", file=sys.stderr)
        sys.exit(1)
    try:
        out = run(["git", "--version"], capture_output=True)
        return out.stdout.strip()
    except Exception as e:
        print(f"Error checking git: {e}", file=sys.stderr)
        sys.exit(1)


def detect_filter_repo_cmd() -> list[str]:
    """Return the preferred invocation for git-filter-repo.

    Tries `git filter-repo` first (plugin style), then `git-filter-repo`.
    """
    try:
        run(["git", "filter-repo", "--help"], capture_output=True)
        return ["git", "filter-repo"]
    except Exception:
        pass
    if which("git-filter-repo"):
        try:
            run(["git-filter-repo", "--help"], capture_output=True)
            return ["git-filter-repo"]
        except Exception:
            pass
    print(
        "Error: git-filter-repo is required. Install from https://github.com/newren/git-filter-repo\n"
        "macOS (Homebrew): brew install git-filter-repo",
        file=sys.stderr,
    )
    sys.exit(1)


def is_git_repo(path: Path) -> bool:
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
        return True
    except Exception:
        return False


def default_clip_name() -> str:
    return _dt.datetime.now().strftime("clip-%Y%m%d-%H%M%S")


def make_clip_paths(out_dir: Path, name: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = out_dir / f"{name}.bundle"
    meta = out_dir / f"{name}.json"
    return bundle, meta


def gather_repo_remotes(repo_dir: Path) -> dict[str, str]:
    remotes = {}
    try:
        out = run(["git", "remote"], cwd=repo_dir, capture_output=True).stdout.strip()
        for r in out.splitlines():
            r = r.strip()
            if not r:
                continue
            try:
                url = run(["git", "remote", "get-url", r], cwd=repo_dir, capture_output=True).stdout.strip()
                remotes[r] = url
            except Exception:
                remotes[r] = ""
    except Exception:
        pass
    return remotes


def detect_default_branch(repo_dir: Path) -> str | None:
    try:
        out = run(["git", "symbolic-ref", "-q", "--short", "HEAD"], cwd=repo_dir, capture_output=True)
        ref = out.stdout.strip()
        if ref:
            return ref
    except Exception:
        pass
    try:
        out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir, capture_output=True)
        ref = out.stdout.strip()
        if ref and ref != "HEAD":
            return ref
    except Exception:
        pass
    return None


def list_tracked_files(repo_dir: Path, path: str) -> list[str]:
    """List tracked files matching a path (file or directory).

    Returns repo-root relative paths.
    """
    try:
        out = run(["git", "ls-files", "--", path], cwd=repo_dir, capture_output=True).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def discover_rename_chain(repo_dir: Path, file_path: str) -> set[str]:
    """Discover prior names of a tracked file by following renames.

    Uses `git log --follow --name-status` and collects old/new paths from R* entries.
    Returns a set including the provided file_path and any discovered historical names.
    """
    names: set[str] = set()
    names.add(file_path)
    try:
        out = run(
            [
                "git",
                "log",
                "--follow",
                "--name-status",
                "--diff-filter=R",
                "--pretty=format:",
                "--",
                file_path,
            ],
            cwd=repo_dir,
            capture_output=True,
        ).stdout
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if parts and parts[0].startswith("R") and len(parts) >= 3:
                oldp = parts[1].strip()
                newp = parts[2].strip()
                if oldp:
                    names.add(oldp)
                if newp:
                    names.add(newp)
    except Exception:
        pass
    return names


def expand_paths_following_renames(repo_dir: Path, paths: list[str], max_files: int = 1000) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Expand input paths to include historical names across renames.

    For files: follow renames via discover_rename_chain.
    For directories: enumerate tracked files under the dir and follow renames for each file (capped by max_files).

    Returns (expanded_paths, details_map, warnings)
    - expanded_paths: unique list of repo-root relative paths to pass to filter-repo.
    - details_map: mapping input path -> list of discovered names (including the input itself).
    - warnings: any warning strings encountered (e.g., directory too large to follow).
    """
    expanded: set[str] = set()
    details: dict[str, list[str]] = {}
    warns: list[str] = []
    for p in paths:
        # Normalize path as provided (repo-root relative)
        tracked = list_tracked_files(repo_dir, p)
        if not tracked:
            # Path might be untracked or not present at HEAD; still include as-is
            expanded.add(p)
            details[p] = [p]
            continue
        # If p resolves to multiple files (directory or glob-like path), handle as directory case
        if len(tracked) == 1 and tracked[0] == p:
            # Single file case
            chain = discover_rename_chain(repo_dir, p)
            expanded.update(chain)
            details[p] = sorted(chain)
        else:
            # Directory or multi-file path
            files = tracked
            if len(files) > max_files:
                warns.append(f"Skipping follow-renames for '{p}' – too many files ({len(files)} > {max_files})")
                expanded.add(p)
                details[p] = [p]
                continue
            agg: set[str] = set()
            for f in files:
                agg.update(discover_rename_chain(repo_dir, f))
            if not agg:
                agg.add(p)
            expanded.update(agg)
            details[p] = sorted(agg)
    return sorted(expanded), details, warns


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Create a Git bundle of selected paths with full history.")
    parser.add_argument("paths", nargs="+", help="File or directory paths to include (relative to repo root)")
    parser.add_argument("-r", "--repo", default=".", help="Path to the source git repository (default: .)")
    parser.add_argument("-t", "--to-subdir", dest="to_subdir", default=None, help="Re-root content under this subdirectory inside the clip")
    parser.add_argument("-o", "--out-dir", default=".git-clipboard", help="Directory to write the clip bundle and metadata (default: ./.git-clipboard)")
    parser.add_argument("-n", "--name", default=default_clip_name(), help="Base name for the clip files (default: clip-YYYYmmdd-HHMMSS)")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing output files if present")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Show what would be included and planned outputs without creating a bundle")
    parser.add_argument("-k", "--keep-temp", action="store_true", help="Keep temporary clone for debugging")
    parser.add_argument("-p", "--prune-source", action="store_true", help="After a successful cut, delete the specified paths from the source repo and commit the removal")
    parser.add_argument("-A", "--require-ack", default=None, help="Path to an ack file produced by git-paste --ack; if provided, pruning only proceeds if ack exists")
    parser.add_argument("--follow-renames", dest="follow_renames", action="store_true", default=True, help="Follow file renames to include historical names (default: on)")
    parser.add_argument("--no-follow-renames", dest="follow_renames", action="store_false", help="Do not follow renames for provided paths")

    args = parser.parse_args(argv)

    git_ver = require_git()
    filter_repo_cmd = detect_filter_repo_cmd()

    src_repo = Path(args.repo).resolve()
    if not is_git_repo(src_repo):
        print(f"Error: {src_repo} is not a git repository", file=sys.stderr)
        sys.exit(1)

    present = [p for p in args.paths if (src_repo / p).exists()]
    if not present:
        print("Warning: none of the specified paths exist in the current working tree. Proceeding anyway…", file=sys.stderr)

    out_dir = Path(args.out_dir).resolve()
    bundle_path, meta_path = make_clip_paths(out_dir, args.name)
    if (bundle_path.exists() or meta_path.exists()) and not args.force and not args.dry_run:
        print(f"Error: {bundle_path.name} or {meta_path.name} already exists in {out_dir}. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    # Prepare path expansion (follow renames) preview from current repo state
    expanded_paths: list[str] = list(args.paths)
    details_map: dict[str, list[str]] = {p: [p] for p in args.paths}
    warnings_list: list[str] = []
    if args.dry_run and args.follow_renames:
        try:
            # Use the source repo for analysis during dry-run
            expanded_paths, details_map, warnings_list = expand_paths_following_renames(src_repo, args.paths)
        except Exception:
            pass

    if args.dry_run:
        try:
            rev_count = run(["git", "rev-list", "--all", "--count", "--", *expanded_paths], cwd=src_repo, capture_output=True).stdout.strip()
        except Exception:
            rev_count = "unknown"
        try:
            sample = run(["git", "log", "--oneline", "-n", "5", "--", *expanded_paths], cwd=src_repo, capture_output=True).stdout.strip()
        except Exception:
            sample = ""
        mapping = []
        for p in expanded_paths:
            dst = f"{args.to_subdir.rstrip('/')}/{p}" if args.to_subdir else p
            mapping.append((p, dst))
        plan = {
            "repo": str(src_repo),
            "paths": args.paths,
            "expanded_paths": expanded_paths if args.follow_renames else args.paths,
            "to_subdir": args.to_subdir,
            "follow_renames": bool(args.follow_renames),
            "follow_details": details_map if args.follow_renames else {},
            "commit_count_touching_paths": rev_count,
            "sample_commits": sample.splitlines(),
            "path_mapping_preview": [{"from": src, "to": dst} for src, dst in mapping],
            "outputs": {"bundle": str(bundle_path), "metadata": str(meta_path), "out_dir": str(out_dir)},
            "warnings": warnings_list,
            "note": "No files created due to --dry-run",
        }
        print(json.dumps(plan, indent=2))
        return 0

    temp_dir = Path(tempfile.mkdtemp(prefix="git-cut-"))
    temp_repo = temp_dir / "repo"
    try:
        run(["git", "clone", "--no-local", "--no-hardlinks", str(src_repo), str(temp_repo)])

        # Expand paths (follow renames) in temp repo if enabled
        if args.follow_renames:
            try:
                expanded_paths, details_map, warnings_list = expand_paths_following_renames(temp_repo, args.paths)
            except Exception:
                expanded_paths = list(args.paths)
                details_map = {p: [p] for p in args.paths}
                warnings_list = []
        else:
            expanded_paths = list(args.paths)
            details_map = {p: [p] for p in args.paths}
            warnings_list = []

        filter_cmd = list(filter_repo_cmd)
        filter_cmd += ["--force"]
        for p in expanded_paths:
            filter_cmd += ["--path", p]
        if args.to_subdir:
            filter_cmd += ["--to-subdirectory-filter", args.to_subdir]

        run(filter_cmd, cwd=temp_repo)

        default_branch = detect_default_branch(temp_repo)

        out_dir.mkdir(parents=True, exist_ok=True)
        if bundle_path.exists() and args.force:
            bundle_path.unlink()
        run(["git", "bundle", "create", str(bundle_path), "--all"], cwd=temp_repo)

        meta = {
            "version": 1,
            "created_at": _dt.datetime.now().isoformat(),
            "source_repo": str(src_repo),
            "paths": args.paths,
            "expanded_paths": expanded_paths,
            "to_subdir": args.to_subdir,
            "follow_renames": bool(args.follow_renames),
            "bundle": str(bundle_path),
            "git_version": git_ver,
            "filter_repo_invocation": " ".join(filter_repo_cmd),
            "default_branch": default_branch,
            "source_remotes": gather_repo_remotes(src_repo),
            "ack_file_suggestion": str(meta_path.with_suffix('.ack')),
            "warnings": warnings_list,
        }
        if meta_path.exists() and args.force:
            meta_path.unlink()
        meta_path.write_text(json.dumps(meta, indent=2))

        print(str(bundle_path))
        print(str(meta_path))

        try:
            home_clip = Path.home() / ".git-clipboard"
            home_clip.mkdir(parents=True, exist_ok=True)
            last = home_clip / "last"
            last.write_text(json.dumps({"bundle": str(bundle_path), "meta": str(meta_path)}, indent=2))
        except Exception as e:
            print(f"Warning: could not update global clipboard pointer: {e}", file=sys.stderr)

        if args.prune_source:
            status = run(["git", "status", "--porcelain"], cwd=src_repo, capture_output=True).stdout.strip()
            if status:
                print("Error: working tree not clean; aborting prune.", file=sys.stderr)
                sys.exit(1)
            if args.require_ack:
                ack_path = Path(args.require_ack)
                if not ack_path.exists():
                    print(f"Error: ack file not found: {ack_path}", file=sys.stderr)
                    sys.exit(1)
            head = run(["git", "rev-parse", "--short", "HEAD"], cwd=src_repo, capture_output=True).stdout.strip()
            run(["git", "rm", "-r", "--ignore-unmatch", *args.paths], cwd=src_repo)
            msg = f"Move to new repo via clip {bundle_path.name} (cut from {head})"
            run(["git", "commit", "-m", msg], cwd=src_repo)
    finally:
        if args.keep_temp:
            print(f"Temp repo kept at: {temp_repo}")
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

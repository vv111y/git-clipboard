#!/usr/bin/env python3
"""
Package entry for git-paste
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd, cwd=None, check=True, capture_output=False, text=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture_output, text=text)


def which(cmd: str):
    return shutil.which(cmd)


def is_git_repo(path: Path) -> bool:
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
        return True
    except Exception:
        return False


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(description="Apply a git-clipboard bundle into a target repo")
    p.add_argument("bundle", nargs="?", help="Path to the .bundle file (optional: defaults to last clip)")
    p.add_argument("-m", "--meta", help="Path to the metadata JSON produced by git-cut (optional)")
    p.add_argument("-r", "--repo", default=".", help="Target repository (default: .)")
    p.add_argument("-b", "--branch", help="Branch to merge into (default: current branch)")
    p.add_argument("-a", "--as-branch", dest="as_branch", help="Name of branch to create from bundle (default: clip/<bundle-name>)")
    p.add_argument("--ref", dest="ref", help="Specific ref to import from the bundle (e.g. 'master' or 'refs/heads/master')")
    p.add_argument("-L", "--list-refs", action="store_true", help="List refs in the bundle and exit (prints JSON)")
    p.add_argument("-M", "--merge", action="store_true", help="Merge the imported branch into --branch/current")
    p.add_argument("-s", "--squash", action="store_true", help="Use a squash merge")
    p.add_argument("-R", "--rebase", action="store_true", help="Rebase the imported branch onto --branch/current before merging")
    p.add_argument("-u", "--remote-name", default=None, help="Optional remote name to add for the bundle (will be removed after)")
    p.add_argument("-F", "--no-ff", action="store_true", help="Disable fast-forward during merge")
    p.add_argument("-j", "--message", default=None, help="Custom merge commit message")
    p.add_argument("-d", "--dry-run", action="store_true", help="Preview import and potential merge/conflicts without changing the repo")
    p.add_argument("-U", "--allow-unrelated-histories", action="store_true", help="Allow merging unrelated histories (recommended for imported clips)")
    p.add_argument("-p", "--prompt-merge", action="store_true", help="After creating import branch, prompt to auto-merge if preview is clean")
    p.add_argument("-T", "--trailers", action="store_true", help="Append clip metadata as commit message trailers on merge/squash commits")
    return p.parse_args(argv)


def current_branch(repo: Path) -> str:
    out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, capture_output=True)
    b = out.stdout.strip()
    if b == "HEAD":
        return "HEAD"
    return b


def has_commits(repo: Path) -> bool:
    try:
        run(["git", "rev-parse", "-q", "--verify", "HEAD"], cwd=repo)
        return True
    except Exception:
        return False


def default_as_branch_name(bundle_path: Path, meta: dict | None) -> str:
    if meta and meta.get("default_branch"):
        base = Path(bundle_path).stem
        return f"clip/{base}"
    return f"clip/{Path(bundle_path).stem}"


def read_meta(meta_path: str | None, bundle_path: Path | None = None) -> dict | None:
    candidate: Path | None = None
    if meta_path:
        candidate = Path(meta_path)
    elif bundle_path is not None:
        candidate = bundle_path.with_suffix('.json')
    if candidate and candidate.exists():
        try:
            return json.loads(candidate.read_text())
        except Exception:
            return None
    return None


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    if not which("git"):
        print("Error: git is required", file=sys.stderr)
        return 1

    if args.bundle:
        bundle = Path(args.bundle).resolve()
    else:
        last_path = Path.home() / ".git-clipboard" / "last"
        if not last_path.exists():
            print("Error: no bundle specified and no last clip pointer found.", file=sys.stderr)
            return 1
        try:
            last = json.loads(last_path.read_text())
            bundle = Path(last.get("bundle", "")).resolve()
            if not bundle.exists():
                print(f"Error: last bundle not found: {bundle}", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"Error reading last clip pointer: {e}", file=sys.stderr)
            return 1
    if not bundle.exists():
        print(f"Error: bundle not found: {bundle}", file=sys.stderr)
        return 1

    if args.list_refs:
        meta_for_list = read_meta(args.meta, bundle)
        out = run(["git", "bundle", "list-heads", str(bundle)], capture_output=True)
        entries = []
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                entries.append({"sha": parts[0], "ref": parts[1]})
        def normalize_for_list(r: str) -> str:
            return r if r.startswith("refs/") else f"refs/heads/{r}"
        payload = {
            "action": "list-refs",
            "bundle": str(bundle),
            "refs": entries,
        }
        if meta_for_list and meta_for_list.get("default_branch"):
            payload["default_ref"] = normalize_for_list(meta_for_list["default_branch"])
        print(json.dumps(payload, indent=2))
        return 0

    repo = Path(args.repo).resolve()
    if not is_git_repo(repo):
        print(f"Error: target is not a git repo: {repo}", file=sys.stderr)
        return 1

    meta = read_meta(args.meta, bundle)
    as_branch = args.as_branch or default_as_branch_name(bundle, meta)

    def build_trailers(ref_used: str | None, head_sha: str | None) -> str:
        lines = []
        lines.append(f"Clip-Bundle: {Path(bundle).name}")
        if meta:
            if meta.get("source_repo"):
                lines.append(f"Clip-Source: {meta['source_repo']}")
            if meta.get("paths"):
                try:
                    lines.append("Clip-Paths: " + ", ".join(meta.get("paths") or []))
                except Exception:
                    pass
            lines.append(f"Clip-Subdir: {meta.get('to_subdir')}")
            lines.append(f"Clip-Created-At: {meta.get('created_at')}")
        if ref_used:
            lines.append(f"Clip-Ref: {ref_used}")
        if head_sha:
            lines.append(f"Clip-Head: {head_sha}")
        return "\n".join(lines)

    heads = run(["git", "bundle", "list-heads", str(bundle)], capture_output=True)
    lines = [line.strip() for line in heads.stdout.splitlines() if line.strip()]
    head_refs = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            head_refs.append(parts[1])

    def normalize_ref(r: str) -> str:
        if r.startswith("refs/"):
            return r
        return f"refs/heads/{r}"

    refspec = None
    sel = None
    if args.ref:
        sel = normalize_ref(args.ref)
        if sel not in head_refs:
            print(f"Error: ref not found in bundle: {args.ref}", file=sys.stderr)
            if head_refs:
                print("Available refs:", file=sys.stderr)
                for r in head_refs:
                    print(f"  - {r}", file=sys.stderr)
            return 1
        refspec = sel
    elif meta and meta.get("default_branch"):
        cand = normalize_ref(meta["default_branch"])
        if cand in head_refs:
            refspec = cand
    if refspec is None and head_refs:
        refspec = head_refs[0]

    work_repo = repo
    temp_dir = None
    remote_name = args.remote_name or f"bundle-{Path(bundle).stem}"
    if args.dry_run:
        temp_dir = Path(tempfile.mkdtemp(prefix="git-paste-dry-"))
        work_repo = temp_dir / "repo"
        run(["git", "clone", "--no-local", "--no-hardlinks", str(repo), str(work_repo)])

    try:
        try:
            run(["git", "remote", "add", remote_name, str(bundle)], cwd=work_repo)
        except Exception:
            try:
                run(["git", "remote", "set-url", remote_name, str(bundle)], cwd=work_repo)
            except Exception:
                pass

        import_head_sha: str | None = None

        def summarize_branch(repo_path: Path, branch: str) -> dict:
            """Summarize branch contents and history.

            Returns commit count, top-level paths, and size estimates including
            total file count, aggregate byte size, and a sample of largest files.
            """
            try:
                cnt = run(["git", "rev-list", "--count", branch], cwd=repo_path, capture_output=True).stdout.strip()
                commit_count = int(cnt) if cnt else 0
            except Exception:
                commit_count = 0
            try:
                names = run(["git", "ls-tree", "--name-only", branch], cwd=repo_path, capture_output=True).stdout.splitlines()
            except Exception:
                names = []
            total_top = len(names)
            MAX_TOP = 50
            top_paths = names[:MAX_TOP]
            file_count = 0
            total_size = 0
            largest: list[tuple[int, str]] = []
            try:
                out = run(["git", "ls-tree", "-r", "--long", branch], cwd=repo_path, capture_output=True).stdout
                for line in out.splitlines():
                    try:
                        meta, path = line.split("\t", 1)
                        parts = meta.split()
                        if len(parts) >= 4 and parts[1] == "blob":
                            size = int(parts[3]) if parts[3].isdigit() else 0
                            file_count += 1
                            total_size += size
                            if len(largest) < 10:
                                largest.append((size, path))
                                largest.sort(reverse=True)
                            else:
                                if size > largest[-1][0]:
                                    largest[-1] = (size, path)
                                    largest.sort(reverse=True)
                    except Exception:
                        continue
            except Exception:
                pass
            largest_files = [{"path": p, "size": s} for s, p in largest]
            return {
                "commit_count": commit_count,
                "top_level_paths": top_paths,
                "top_level_paths_total": total_top,
                "top_level_paths_truncated": bool(total_top > MAX_TOP),
                "file_count": file_count,
                "total_size_bytes": total_size,
                "largest_files": largest_files,
            }

        def diff_sampling(repo_path: Path, left: str, right: str) -> dict:
            """Summarize changes from left..right with a small sample."""
            changes_sample = []
            try:
                ns = run(["git", "diff", "--name-status", "--find-renames=50%", f"{left}..{right}"], cwd=repo_path, capture_output=True).stdout
                for line in ns.splitlines()[:50]:
                    parts = line.split("\t")
                    if not parts:
                        continue
                    code = parts[0]
                    if code.startswith("R") and len(parts) >= 3:
                        changes_sample.append({"status": "R", "from": parts[1], "to": parts[2]})
                    elif len(parts) >= 2:
                        changes_sample.append({"status": code, "path": parts[1]})
            except Exception:
                pass
            files_changed = insertions = deletions = 0
            try:
                ss = run(["git", "diff", "--shortstat", f"{left}..{right}"], cwd=repo_path, capture_output=True).stdout.strip()
                import re as _re
                m_files = _re.search(r"(\d+) files? changed", ss)
                m_ins = _re.search(r"(\d+) insertions?\(\+\)", ss)
                m_del = _re.search(r"(\d+) deletions?\(-\)", ss)
                files_changed = int(m_files.group(1)) if m_files else 0
                insertions = int(m_ins.group(1)) if m_ins else 0
                deletions = int(m_del.group(1)) if m_del else 0
            except Exception:
                pass
            return {
                "range": f"{left}..{right}",
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
                "changes_sample": changes_sample,
            }

        if refspec:
            if args.dry_run:
                run(["git", "fetch", remote_name, f"{refspec}:{as_branch}"], cwd=work_repo)
                import_head_sha = run(["git", "rev-parse", as_branch], cwd=work_repo, capture_output=True).stdout.strip()
                summary = summarize_branch(work_repo, as_branch)
                print(json.dumps({
                    "action": "import-branch",
                    "as_branch": as_branch,
                    "source_ref": refspec,
                    "remote": remote_name,
                    "head": import_head_sha,
                    "source_summary": summary,
                }, indent=2))
            else:
                run(["git", "fetch", remote_name, f"{refspec}:{as_branch}"], cwd=work_repo)
                import_head_sha = run(["git", "rev-parse", as_branch], cwd=work_repo, capture_output=True).stdout.strip()
        else:
            if args.dry_run:
                run(["git", "fetch", remote_name, f"refs/heads/*:refs/remotes/{remote_name}/*"], cwd=work_repo)
                out = run(["git", "branch", "-r"], cwd=work_repo, capture_output=True)
                rheads = [line.strip() for line in out.stdout.splitlines() if line.strip().startswith(f"{remote_name}/")]
                if not rheads:
                    print("Error: no heads found in bundle", file=sys.stderr)
                    return 1
                src = rheads[0]
                run(["git", "branch", as_branch, src], cwd=work_repo)
                import_head_sha = run(["git", "rev-parse", as_branch], cwd=work_repo, capture_output=True).stdout.strip()
                summary = summarize_branch(work_repo, as_branch)
                print(json.dumps({
                    "action": "import-branch",
                    "as_branch": as_branch,
                    "source_ref": src,
                    "remote": remote_name,
                    "head": import_head_sha,
                    "source_summary": summary,
                }, indent=2))
            else:
                run(["git", "fetch", remote_name, f"refs/heads/*:refs/remotes/{remote_name}/*"], cwd=work_repo)
                out = run(["git", "branch", "-r"], cwd=work_repo, capture_output=True)
                rheads = [line.strip() for line in out.stdout.splitlines() if line.strip().startswith(f"{remote_name}/")]
                if not rheads:
                    print("Error: no heads found in bundle", file=sys.stderr)
                    return 1
                src = rheads[0]
                run(["git", "branch", as_branch, src], cwd=work_repo)
                import_head_sha = run(["git", "rev-parse", as_branch], cwd=work_repo, capture_output=True).stdout.strip()

        if not args.dry_run:
            print(f"Imported branch: {as_branch}")

        obvious_mode = (not args.merge and not args.squash and not args.rebase and not args.dry_run and not args.prompt_merge)

        if args.merge or args.squash or args.rebase or args.dry_run or obvious_mode:
            repo_has_commits = has_commits(work_repo)
            target_branch = args.branch or (current_branch(work_repo) if repo_has_commits else None)
            if not repo_has_commits:
                if args.dry_run or obvious_mode:
                    print(json.dumps({
                        "action": "merge-preview",
                        "target": None,
                        "source": as_branch,
                        "note": "Target repo has no commits; merge would effectively adopt imported branch after creation.",
                        "conflicts": False
                    }, indent=2))
                else:
                    print("Target repo has no commits; skipping merge. Imported branch created.")
                return 0
            if target_branch == "HEAD":
                print("Error: cannot merge onto detached HEAD. Specify --branch.", file=sys.stderr)
                return 1
            run(["git", "rev-parse", "--verify", target_branch], cwd=work_repo)

            if not args.dry_run:
                run(["git", "checkout", target_branch], cwd=work_repo)

            if args.rebase:
                if args.dry_run or obvious_mode:
                    print(json.dumps({
                        "action": "rebase",
                        "branch": as_branch,
                        "onto": target_branch
                    }, indent=2))
                else:
                    run(["git", "rebase", target_branch, as_branch], cwd=work_repo)
                    run(["git", "checkout", target_branch], cwd=work_repo)

            merge_cmd = ["git", "merge"]
            if args.squash:
                merge_cmd.append("--squash")
            if args.no_ff:
                merge_cmd.append("--no-ff")
            if args.allow_unrelated_histories:
                merge_cmd.append("--allow-unrelated-histories")
            if args.message:
                merge_cmd += ["-m", args.message]
                if args.trailers:
                    merge_cmd += ["-m", build_trailers(refspec, import_head_sha)]
            merge_cmd.append(as_branch)

            if args.dry_run or obvious_mode:
                try:
                    base = run(["git", "merge-base", target_branch, as_branch], cwd=work_repo, capture_output=True).stdout.strip()
                except Exception:
                    base = ""
                conflicts = None
                if base:
                    output = run(["git", "merge-tree", base, target_branch, as_branch], cwd=work_repo, capture_output=True).stdout
                    conflicts = ("<<<<<<<" in output or ">>>>>>>" in output)
                summary = summarize_branch(work_repo, as_branch)
                diff = diff_sampling(work_repo, base if base else target_branch, as_branch)
                print(json.dumps({
                    "action": "merge-preview",
                    "target": target_branch,
                    "source": as_branch,
                    "no_ff": args.no_ff,
                    "squash": args.squash,
                    "conflicts": conflicts,
                    "allow_unrelated_histories": args.allow_unrelated_histories,
                    "auto_allow_unrelated_histories": (not base),
                    "trailers": bool(args.trailers),
                    "source_summary": summary,
                    "diff_summary": diff,
                    "note": None if base else "Could not determine merge-base; conflict status unknown"
                }, indent=2))
                if obvious_mode and conflicts is False:
                    ans = input("Auto-merge now? [y/N]: ").strip().lower()
                    if ans not in ("y", "yes"):
                        print("Merge skipped by user.")
                        return 0
                    if not base and "--allow-unrelated-histories" not in merge_cmd:
                        merge_cmd.insert(2, "--allow-unrelated-histories")
                    run(merge_cmd, cwd=work_repo)
                    if args.squash:
                        msg = args.message or f"Squash import from {as_branch}"
                        if args.trailers:
                            msg = f"{msg}\n\n{build_trailers(refspec, import_head_sha)}"
                        run(["git", "commit", "-m", msg], cwd=work_repo)
                    else:
                        if args.trailers and not args.message:
                            existing = run(["git", "log", "-1", "--pretty=%B"], cwd=work_repo, capture_output=True).stdout
                            new_msg = f"{existing.strip()}\n\n{build_trailers(refspec, import_head_sha)}"
                            run(["git", "commit", "--amend", "-m", new_msg], cwd=work_repo)
                    if not args.dry_run:
                        print(f"Merged {as_branch} into {target_branch}")
                    return 0
                elif obvious_mode:
                    print("Conflicts likely or unknown; not auto-merging.")
                    return 0
            elif args.prompt_merge:
                try:
                    base = run(["git", "merge-base", target_branch, as_branch], cwd=work_repo, capture_output=True).stdout.strip()
                except Exception:
                    base = ""
                conflicts = None
                if base:
                    output = run(["git", "merge-tree", base, target_branch, as_branch], cwd=work_repo, capture_output=True).stdout
                    conflicts = ("<<<<<<<" in output or ">>>>>>>" in output)
                print(json.dumps({
                    "action": "merge-preview",
                    "target": target_branch,
                    "source": as_branch,
                    "no_ff": args.no_ff,
                    "squash": args.squash,
                    "conflicts": conflicts,
                    "allow_unrelated_histories": args.allow_unrelated_histories,
                    "trailers": bool(args.trailers),
                    "note": None if base else "Could not determine merge-base; conflict status unknown"
                }, indent=2))
                if conflicts is False:
                    ans = input("Auto-merge now? [y/N]: ").strip().lower()
                    if ans not in ("y", "yes"):
                        print("Merge skipped by user.")
                        return 0
                else:
                    print("Conflicts likely or unknown; not auto-merging.")
                    return 0
            else:
                try:
                    base = run(["git", "merge-base", target_branch, as_branch], cwd=work_repo, capture_output=True).stdout.strip()
                except Exception:
                    base = ""
                if not base and "--allow-unrelated-histories" not in merge_cmd:
                    merge_cmd.insert(2, "--allow-unrelated-histories")
                run(merge_cmd, cwd=work_repo)

            if args.squash and not (args.dry_run or obvious_mode):
                msg = args.message or f"Squash import from {as_branch}"
                if args.trailers:
                    msg = f"{msg}\n\n{build_trailers(refspec, import_head_sha)}"
                run(["git", "commit", "-m", msg], cwd=work_repo)

            if not (args.dry_run or obvious_mode) and not args.squash and args.trailers and not args.message:
                existing = run(["git", "log", "-1", "--pretty=%B"], cwd=work_repo, capture_output=True).stdout
                new_msg = f"{existing.strip()}\n\n{build_trailers(refspec, import_head_sha)}"
                run(["git", "commit", "--amend", "-m", new_msg], cwd=work_repo)

            if not args.dry_run:
                print(f"Merged {as_branch} into {target_branch}")

    finally:
        if args.remote_name is None and not args.dry_run:
            try:
                run(["git", "remote", "remove", remote_name], cwd=repo)
            except Exception:
                pass
        if args.dry_run and temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

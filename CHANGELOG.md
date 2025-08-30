# Changelog

All notable changes to this project will be documented in this file.

## v0.2.1 — 2025-08-30

Packaging and richer dry-run previews.

### Features (v0.2.1)

- Packaging
  - Converted to a proper Python package (src layout) with console entry points:
    - git-cut, git-paste, git-clipboard
  - Added pyproject.toml (hatchling backend) and version bumped to 0.2.1.
- git-paste (dry-run v2)
  - Source summary now includes file_count, total_size_bytes, and largest_files.
  - Added diff_summary with range, files_changed, insertions, deletions, and a sample of changes.
- git-paste
  - New `--list-refs` (`-L`) to enumerate bundle heads as JSON (with default_ref when metadata is present).

### Tests (v0.2.1)

- Refactored e2e.sh into functions per scenario for readability and faster targeting.
- Validated new dry-run fields and list-refs through end-to-end runs.

### Docs (v0.2.1)

- README updated with pipx install note and documentation for new dry-run fields and list-refs.

### Notes (v0.2.1)

- Homebrew packaging is deferred; prefer pipx for now.

## v0.2.0 — 2025-08-30

Ref selection on paste, commit message trailers, short flags, and status utility.

### Features (v0.2.0)

- git-paste
  - New `--ref` option to select a specific ref from the bundle (e.g., `--ref main` or `refs/heads/main`).
  - New `--trailers` option to append clip provenance as commit message trailers on merges and squashes:
    - Clip-Bundle, Clip-Source, Clip-Paths, Clip-Subdir, Clip-Created-At, Clip-Ref, Clip-Head.
  - Obvious mode and prompted preview JSON now include `trailers` flag.
  - Keeps default merge message when no `--message` is provided; trailers are appended via amend.

- git-cut / git-paste
  - Added short flags for frequent options (e.g., -r, -d, -m, -p, -T).

- git-clipboard
  - New helper to display the current clipboard pointer and basic clip metadata.

### Tests (v0.2.0)

- Extended e2e to cover:
  - Clipboard default (no-arg paste) and obvious-mode auto-merge prompt.
  - Merge with `--trailers` and Squash with `--trailers` (assert Clip-* lines exist, including Clip-Ref and Clip-Head).

### Docs (v0.2.0)

- README updated with `--ref` selection, and a new Trailers section with examples.

### Notes (v0.2.0)

- Dry-run previews unaffected (no repo changes); trailers flag is surfaced in preview JSON.


## v0.1.0 — 2025-08-30

Initial public cut/paste workflow with safety, previews, and a smooth default UX.

 
### Features

- git-cut
  - Creates filtered history clips using git-filter-repo (with optional --to-subdir).
  - Produces a portable .bundle and a metadata .json sidecar.
  - Writes a clipboard pointer at ~/.git-clipboard/last for easy pasting.
  - Optional "true move" via --prune-source and --require-ack.

- git-paste
  - Imports a clip into a target repo as a new branch (clip/\<name\> by default).
  - Dry-run previews import and potential conflicts (via merge-tree) in a temp clone.
  - Prompted merge (--prompt-merge) and “obvious mode” (no flags): preview and offer auto-merge if clean.
  - Automatically adds --allow-unrelated-histories when merge-base is missing during real merges.
  - Supports --merge, --squash, --rebase, --no-ff, custom message, and optional --branch.
  - Defaults to the last clip if no bundle path is provided (clipboard default).

### Tests

- End-to-end script (e2e.sh) covering:
  - Standard import and merge.
  - Squash import.
  - Conflict preview after divergence.
  - Prune-source workflow.
  - Clipboard default (no-arg paste) and obvious-mode auto-merge prompt (confirmed).

### Docs

- README documents install, usage, clipboard default, obvious mode, and a quick “Try it” section.

### Notes

- Requires git and git-filter-repo to be installed.
- Bundles are created with --all refs from the filtered repo for portability.

### Known gaps / next steps

- Paste: select specific ref from a bundle (by name or metadata default).
- Optional source metadata recording (git-notes or trailers).
- Submodules/LFS handling options.
- Richer dry-run with file lists and size estimates.
- Convenience: status of the clipboard state and short single-letter flags.

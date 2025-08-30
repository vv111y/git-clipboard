# Roadmap / TODOs

- [done] feat_true_cut.md: Implement the true cut workflow (prune-source + optional require-ack)
- [done] Paste: select ref from bundle (by name or from metadata default)
- [done] Paste: commit message trailers for provenance (Clip-Bundle/Source/Paths/Subdir/Created-At/Ref/Head)
- [later] Paste: optionally record source metadata as git-notes (deferred; trailers cover the need for now)
- Cut: multiple path remappings (a/b -> x/y, c -> z)
- Submodules/LFS handling options
- Dry-run enhancements v1: include commit count and top-level path summary in preview JSON
- Dry-run enhancements v2: size estimates and changed file sampling
- [done] Tests: expand E2E scenarios (conflicts, rebase mode, squash merge, prune, clipboard default)
- [done] Paste: clipboard default (uses ~/.git-clipboard/last when bundle omitted)
- [done] Paste: obvious mode (preview + prompt + auto-merge when clean)
- Tests: unitized test for obvious mode prompt path (added in e2e; consider splitting into shell functions)
- Docs: document obvious mode and clipboard default with an example

Added by Willy:

- [done] git-clipboard: gives status of the clipboard state
- [done] Single-letter CLI flags alternatives, for less typing

Proposed small conveniences

- git-paste: `--list-refs` to show heads available in the bundle and exit
- Packaging: Homebrew tap or simple install script; optional pipx wrapper
- Windows support audit (paths and quoting) and docs

Next up (picked)

- Dry-run enhancements v1: add commit count and top-level path summary to dry-run JSON outputs (import-branch, merge-preview)

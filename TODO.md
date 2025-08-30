# Roadmap / TODOs

- [done] feat_true_cut.md: Implement the true cut workflow (prune-source + optional require-ack)
- [done] Paste: select ref from bundle (by name or from metadata default)
- [done] Paste: commit message trailers for provenance (Clip-Bundle/Source/Paths/Subdir/Created-At/Ref/Head)
- [cancel] multiple path remappings (a/b -> x/y, c -> z)
- [done] Dry-run enhancements v1: include commit count and top-level path summary in preview JSON
- [done] Tests: expand E2E scenarios (conflicts, rebase mode, squash merge, prune, clipboard default)
- [done] Paste: clipboard default (uses ~/.git-clipboard/last when bundle omitted)
- [done] Paste: obvious mode (preview + prompt + auto-merge when clean)
- [done] git-clipboard: gives status of the clipboard state
- [done] Single-letter CLI flags alternatives, for less typing
- [done] git-paste: `--list-refs` to show heads available in the bundle and exit
- [done] Dry-run enhancements v2: size estimates and changed file sampling
- [done] Docs: document obvious mode and clipboard default with an example

BackLog

- Packaging: 1) pipx wrapper, 2) Homebrew tap or simple install script; 
- Submodules/LFS handling options
- [later] Windows support audit (paths and quoting) and docs
- [later] Paste: optionally record source metadata as git-notes (deferred; trailers cover the need for now)

Next up (picked)

- Tests: obvious mode prompt covered in e2e; optional unit test or refactor e2e into shell functions

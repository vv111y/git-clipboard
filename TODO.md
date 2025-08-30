# Roadmap / TODOs

- [done] feat_true_cut.md: Implement the true cut workflow (prune-source + optional require-ack)
- Paste: select ref from bundle (by name or from metadata default)
- Paste: optionally record source metadata as git-notes or commit message trailer
- Cut: multiple path remappings (a/b -> x/y, c -> z)
- Submodules/LFS handling options
- Dry-run enhancements: more detailed file lists and size estimates
- [done] Tests: expand E2E scenarios (conflicts, rebase mode, squash merge, prune, clipboard default)
- [done] Paste: clipboard default (uses ~/.git-clipboard/last when bundle omitted)
- [done] Paste: obvious mode (preview + prompt + auto-merge when clean)
- Tests: unitized test for obvious mode prompt path (added in e2e; consider splitting into shell functions)
- Docs: document obvious mode and clipboard default with an example

Added by Willy:

- [done] git-clipboard: gives status of the clipboard state
- [done] Single-letter CLI flags alternatives, for less typing

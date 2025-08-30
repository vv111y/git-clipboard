# git-clipboard

Convenience CLI wrappers to cut and paste Git history using git-filter-repo and bundles.

- git-cut: produce a portable bundle containing only selected paths and their full history.
- git-paste: import that bundle into another repository, preserving history and optionally merging.

The heavy lifting is done by git-filter-repo; these commands try to make common flows one-liners.

## Install

- Requirements: git, git-filter-repo
- macOS: `brew install git-filter-repo`

Make the scripts executable and add this folder to your PATH or symlink them:

```bash
chmod +x git-cut git-paste
# optional, symlink somewhere on PATH
ln -s "$PWD/git-cut" /usr/local/bin/git-cut
ln -s "$PWD/git-paste" /usr/local/bin/git-paste
```

## git-cut

Create a bundle containing only the specified paths (files/folders) and their history. The source repo is never modified.

Usage

```bash
git-cut [PATH ...] [--repo REPO] [--to-subdir DIR] [--out-dir DIR] [--name NAME] [--force]
```

### Key options

- -r/--repo: path to the source repository (default: current dir)
- -t/--to-subdir: re-root the content into a subdirectory inside the clip
- -o/--out-dir: where to write the .bundle and .json (default: ./.git-clipboard)
- -n/--name: base filename for the outputs (default: clip-YYYYmmdd-HHMMSS)
- -f/--force: overwrite existing outputs
- -d/--dry-run: print a JSON plan without creating output files

### Outputs

- NAME.bundle: a git bundle with all refs from the filtered repo
- NAME.json: metadata capturing paths, subdir, source remotes, and default branch
- The last clip pointer is also written to ~/.git-clipboard/last for easy pasting without specifying a path.

## git-paste

Import a previously created bundle into a target repository. By default it creates a new branch from the bundle and you can choose to merge it.

Usage

```bash
git-paste [BUNDLE] [-m META.json] [-r REPO] [-a NAME] [-b BRANCH] [--merge|-M|--squash|-s|--rebase|-R] [--no-ff|-F] [--message|-j MSG] [--dry-run|-d] [--allow-unrelated-histories|-U] [--prompt-merge|-p]
```

### Default behavior

- Creates a branch `clip/<bundle-base-name>` from the bundle's first head
- If --merge/--squash/--rebase is given, merges into the current branch (or --branch)
- Cleans up a temporary remote used for fetching from the bundle

### Clipboard default and obvious mode

- If BUNDLE is omitted, git-paste looks up the last clip pointer at `~/.git-clipboard/last` written by git-cut, and uses that bundle.
- If you pass no merge flags, git-paste runs a quick merge preview and, if clean, prompts whether to auto-merge the imported branch into the current (or --branch) target. If conflicts are likely or unknown, it won’t auto-merge.

Example (clipboard + obvious mode):

```bash
# In source repo
git-cut path/to/subtree --out-dir ../clips --to-subdir imported

# In target repo, just paste with no args. If clean, confirm to auto-merge.
git-paste
```

### Notes for dry-run

- With `--dry-run`, paste clones the target repo into a temporary directory, simulates the import and prints a JSON summary, and previews merge conflicts using `git merge-tree` when possible. The real repo is not modified.
- Use `--allow-unrelated-histories` when you later perform a real merge of unrelated histories (often required for fresh repos).
- Use `--prompt-merge` to preview conflicts and, if clean, interactively confirm an automatic merge.

## Notes and assumptions

- Assumes git-filter-repo is installed and available as either `git filter-repo` or `git-filter-repo`.
- `git-cut` clones your repository into a temp directory, filters there, and never touches your working copy.
- We bundle `--all` refs after filtering to maximize portability; paste selects the first head by default.
- If you used `--to-subdir` when cutting, the directory structure is already remapped inside the bundle; paste doesn’t need to move files.
- Merge strategies in paste are standard Git merge/rebase flows; resolve conflicts as usual if they arise.

## Examples

Cut history of two folders and paste into another repo under a new branch, then merge:

```bash
# from source repo
git-cut dotfiles/.config nvim/ --to-subdir configs --out-dir ../clips

# in target repo
git-paste ../clips/clip-20250101-120000.bundle --dry-run --merge
# If clean, perform the merge (often with unrelated histories allowed):
git-paste ../clips/clip-20250101-120000.bundle --merge --allow-unrelated-histories --message "Import configs"
```

## Try it

Quick smoke test and demo:

```bash
# Make the scripts executable (once)
chmod +x git-cut git-paste

# Run the end-to-end test; it prints JSON previews and ends with "E2E OK"
bash ./e2e.sh
```

Minimal clipboard flow:

```bash
# In a source repo
git-cut some/path --to-subdir imported

# In a target repo
git-paste   # uses the last clip; if clean, confirm to auto-merge
```

## Tests

Run the end-to-end test script (creates temporary repos, cuts, dry-runs paste, then imports and merges):

```bash
bash ./e2e.sh
```

## Troubleshooting

- If you see `git: 'filter-repo' is not a git command`, install git-filter-repo.
- Bundles list heads: `git bundle list-heads path/to.bundle`.
- You can delete the generated branch and retry paste safely; the origin repo is never modified by these tools.

## License

MIT

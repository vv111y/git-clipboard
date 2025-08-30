ultimately those files/folders will go to the intended target repo. when I git-paste in the target repo, both the files/folders and their histories are now moved to the new repo. it should be a move: the files/folders are deleted from the source repo.

Short answer: today your scripts do a **copy**, not a **move**. To make it a true **move** you add a prune step in the source repo after a successful paste.

# How to use it end-to-end (ELI5)

1. **Cut from the source repo**
   Keeps only the paths you want and packs their full history into one file.

```bash
# in SOURCE repo
git-cut apps/foo lib/foo --to-subdir foo/ --out-dir ../clips
# → creates ../clips/clip-YYYYmmdd-HHMMSS.bundle + .json
```

* `--to-subdir foo/` only changes the layout **inside the clip**. It does not touch the source repo.

2. **Paste into the target repo**
   Brings files + history into a new branch, then you merge how you like.

```bash
# in TARGET repo
git-paste ../clips/clip-*.bundle           # creates branch: clip/clip-*
git merge --no-ff clip/clip-*              # or: git-paste ... --merge/--squash/--rebase
```

3. **Prune the source (this makes it a MOVE)**
   After you confirm the target has the content you want, delete those paths in the source repo.

* Safe, non-rewriting option (recommended):

```bash
# in SOURCE repo
git rm -r apps/foo lib/foo
git commit -m "Move foo to <target-repo> via bundle clip-YYYYmmdd-HHMMSS"
```

This removes the files going forward but keeps their past history, which is what you usually want.

* Optional, history-rewrite option (advanced, coordinate with collaborators):

```bash
# in SOURCE repo (removes those paths from ALL history)
git filter-repo --path apps/foo --path lib/foo --invert-paths
# then force-push the rewritten repo
git push --force-with-lease
```

# Proposed script tweak to streamline “move”

* Add `git-cut --prune-source apps/foo lib/foo` which, **after** writing the bundle, runs:

  * safety checks: clean working tree, on main branch, records the source HEAD used for the cut,
  * `git rm -r … && git commit -m "Move … via clip <id>"`.
* Optional handshake: `git-paste --ack <meta.json>` writes an `.ack` file containing the bundle hash. Then `git-cut --prune-source --require-ack <ackfile>` only prunes if the paste happened to the intended target.

# Net effect

* Cut = prepare portable history.
* Paste = import that history to the target.
* Prune = delete from source so the net effect is a **move** across repos with history preserved where it belongs.

If you want, I’ll add `--prune-source` and `--require-ack` to the scripts now.

#!/usr/bin/env bash
# e2e.sh: End-to-end tests for git-clipboard (git-cut and git-paste)
# Creates temporary repos, commits sample content, cuts a subset, and pastes into a target repo.
# Prints JSON and key git logs to validate behavior. Exits non-zero on failures.

set -euo pipefail

TMP_ROOT="$(mktemp -d -t gc-e2e-XXXX)"
SRC="$TMP_ROOT/src"
DST="$TMP_ROOT/dst"
CLIPS="$TMP_ROOT/clips"
DST2="$TMP_ROOT/dst2"
DST3="$TMP_ROOT/dst3"
DST4="$TMP_ROOT/dst4"
DST5="$TMP_ROOT/dst5"
DST6="$TMP_ROOT/dst6"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

mkdir -p "$SRC" "$DST" "$CLIPS" "$DST2" "$DST3" "$DST4" "$DST5" "$DST6"

git -C "$SRC" init -q
mkdir -p "$SRC/proj/a" "$SRC/proj/b"
echo one > "$SRC/proj/a/file1.txt"
echo two > "$SRC/proj/b/file2.txt"
git -C "$SRC" add .
git -C "$SRC" commit -qm "init"

echo three > "$SRC/proj/a/file3.txt"
git -C "$SRC" add .
git -C "$SRC" commit -qm "feat: add file3"

# Cut only proj/a into a clip under subdir 'imported'
CLIP_NAME="clip-test"
"$(pwd)/git-cut" proj/a --repo "$SRC" --to-subdir imported --out-dir "$CLIPS" --name "$CLIP_NAME"

# Verify outputs exist
[ -s "$CLIPS/$CLIP_NAME.bundle" ]
[ -s "$CLIPS/$CLIP_NAME.json" ]

# Scenario 0: Paste using clipboard default (no bundle arg)
git -C "$DST3" init -q
"$(pwd)/git-paste" --repo "$DST3" --dry-run | sed -n '1,80p'
"$(pwd)/git-paste" --repo "$DST3" | sed -n '1,40p'
if ! git -C "$DST3" branch --list | grep -q "clip/$CLIP_NAME"; then
  echo "ERROR: expected imported branch clip/$CLIP_NAME not found in DST3" >&2
  exit 1
fi

# Dry-run paste into target
git -C "$DST" init -q
BR_DST=$(git -C "$DST" symbolic-ref -q --short HEAD || echo master)
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST" --dry-run --merge | sed -n '1,120p'

# Actual paste: import branch then (no commits, so create initial commit and merge)
git -C "$DST" commit --allow-empty -qm "chore: initial"
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST" --merge --allow-unrelated-histories --message "Import clip"

echo "== Log after merge =="
git -C "$DST" log --graph --oneline --decorate -n 10

echo "== Tree =="
git -C "$DST" ls-tree -r --name-only HEAD | sed -n '1,40p'

# Scenario 2: Squash import into a new target repo
git -C "$DST2" init -q
BR_DST2=$(git -C "$DST2" symbolic-ref -q --short HEAD || echo master)
git -C "$DST2" commit --allow-empty -qm "chore: initial"
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST2" --merge --squash --allow-unrelated-histories --message "Squash Import"
echo "== Squash Log =="
git -C "$DST2" log --oneline -n 3 | sed -n '1,3p'
echo "== Squash Tree =="
git -C "$DST2" ls-tree -r --name-only HEAD | sed -n '1,40p'

# Scenario 3: Conflict preview after diverging changes (now branches share history)
git -C "$DST" checkout "$BR_DST" -q
echo "local" >> "$DST/imported/proj/a/file1.txt"
git -C "$DST" add -A && git -C "$DST" commit -qm "local: change file1"
git -C "$DST" checkout clip/clip-test -q
echo "clip" >> "$DST/imported/proj/a/file1.txt"
git -C "$DST" add -A && git -C "$DST" commit -qm "clip: change file1"
git -C "$DST" checkout "$BR_DST" -q
echo "== Conflict preview =="
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST" --dry-run --merge | sed -n '1,120p'

# Scenario 4: Prune source
"$(pwd)/git-cut" proj/a --repo "$SRC" --out-dir "$CLIPS" --name prune-test --prune-source
if git -C "$SRC" ls-files | grep -q '^proj/a/'; then
  echo "ERROR: prune failed: proj/a still present" >&2
  exit 1
fi
echo "== Source log after prune =="
git -C "$SRC" log -1 --pretty=%B | sed -n '1,4p'

# Scenario 5: Obvious mode auto-merge prompt (clean merge path)
git -C "$DST4" init -q
BR_DST4=$(git -C "$DST4" symbolic-ref -q --short HEAD || echo master)
git -C "$DST4" commit --allow-empty -qm "chore: initial"
# First, seed the repo with a real merge so histories are related
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST4" --merge --allow-unrelated-histories --message "seed import" | sed -n '1,120p'
# Add a trivial commit on master to ensure a non-trivial but clean merge
echo note >> "$DST4/README.txt" || true
git -C "$DST4" add -A && git -C "$DST4" commit -qm "chore: note"
# Now run obvious mode (no flags) and auto-confirm; use printf to avoid SIGPIPE from yes
printf 'y\n' | "$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST4" | sed -n '1,120p'
echo "== Obvious Mode Log =="
git -C "$DST4" log --graph --oneline --decorate -n 8 | sed -n '1,120p'

# Scenario 6: Merge with trailers appended to commit message
git -C "$DST5" init -q
BR_DST5=$(git -C "$DST5" symbolic-ref -q --short HEAD || echo master)
git -C "$DST5" commit --allow-empty -qm "chore: initial"
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST5" --merge --allow-unrelated-histories --message "Import clip" --trailers | sed -n '1,120p'
LAST_MSG=$(git -C "$DST5" log -1 --pretty=%B)
echo "== Merge with trailers commit message =="
echo "$LAST_MSG" | sed -n '1,80p'
echo "$LAST_MSG" | grep -q "Clip-Bundle:" || { echo "ERROR: expected Clip-Bundle trailer in merge commit" >&2; exit 1; }
echo "$LAST_MSG" | grep -q "Clip-Ref:" || { echo "ERROR: expected Clip-Ref trailer in merge commit" >&2; exit 1; }
echo "$LAST_MSG" | grep -q "Clip-Head:" || { echo "ERROR: expected Clip-Head trailer in merge commit" >&2; exit 1; }

# Scenario 7: Squash with trailers appended to commit message
git -C "$DST6" init -q
BR_DST6=$(git -C "$DST6" symbolic-ref -q --short HEAD || echo master)
git -C "$DST6" commit --allow-empty -qm "chore: initial"
"$(pwd)/git-paste" "$CLIPS/$CLIP_NAME.bundle" --repo "$DST6" --merge --squash --allow-unrelated-histories --message "Squash Import" --trailers | sed -n '1,120p'
LAST_MSG2=$(git -C "$DST6" log -1 --pretty=%B)
echo "== Squash with trailers commit message =="
echo "$LAST_MSG2" | sed -n '1,80p'
echo "$LAST_MSG2" | grep -q "Clip-Bundle:" || { echo "ERROR: expected Clip-Bundle trailer in squash commit" >&2; exit 1; }
echo "$LAST_MSG2" | grep -q "Clip-Ref:" || { echo "ERROR: expected Clip-Ref trailer in squash commit" >&2; exit 1; }
echo "$LAST_MSG2" | grep -q "Clip-Head:" || { echo "ERROR: expected Clip-Head trailer in squash commit" >&2; exit 1; }

echo "E2E OK: $TMP_ROOT"

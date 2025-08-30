DO NOW: I’ll add end-to-end tests (temp repos), and dry-run previews.

## Questions for you
- Should paste support selecting a specific ref inside the bundle (e.g., matching the metadata’s default branch) instead of “first head”?
TODO LATER

- Do you want paste to optionally honor original remotes (from metadata) and record them as notes or in commit messages?
AS OPTION, Q: WHERE WOULD NOTES GO?

- Should git-cut support multiple path remappings (e.g., map a/b -> x/y, c -> z) instead of a single `--to-subdir`?
YES BUT DISCUSS 1ST, HOW WOULD YOU DO THIS?

- Do you want a “dry-run” mode showing what would be kept/renamed before executing?
YES, NOW

- Should we support submodule rewriting (convert submodules to folders or include submodule histories) and/or LFS fetch?
TODO LATER

- Preferred default for paste: just create the import branch (current), or auto-merge into current branch unless flagged otherwise?
1. create import branch
2. dry-run merge, if no conflicts report to user and offer to auto-merge (Y/N)

- ALSO: read  feat_true_cut.md, we want to implement that 

----------------
- add TODO: 
- git-clipboard: gives status of the clipboard state. 
motivation, somebody does a cut but is busy, comes back to job and needs to know what he was trying to do, or to show that the clipboard is in use and what is there before trying another cut&paste

- TODO NOW: by default give notice about merge: whether it is safe, or list which files/folders are in conflict. Automatically do a merge dry-run check. then a short git-paste followup command can do the merge onto the current branch, with the type of merge selected by the args you already provided.

common workflow for me will look something like:
> git-cut file-a dir-b .
> cd <to-other-repo>
> git-paste
-- pasted xxx into new branch yyyy. no conflicts with current branch zzz
> git-paste --merge "adding file a,dir b from repo c" 

I don't think this should be exposed, goal is to simplify, the scripts should know when to use this:
- Use `--allow-unrelated-histories` when you later perform a real merge of unrelated histories (often required for fresh repos).


- TODO source pruning. By default this should act like dd in file managers. the original is untouched until a successful paste to the target repo. then the source is pruned 
  parser.add_argument("--prune-source", action="store_true", help="After a successful cut, delete the specified paths from the source repo and commit the removal")


- ?? Makes a temporary clone of your repo so the original is untouched. -> might be too costly, it will work for my use now, but we will want a switch to provide an alternative



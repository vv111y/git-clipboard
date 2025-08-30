# Contributing

Thanks for your interest in git-clipboard!

## Dev setup

- Requirements: git, Python 3.8+, git-filter-repo
- Optional: pipx for installing the package locally

## Run tests

```bash
bash ./e2e.sh
```

## Release checklist

- Update CHANGELOG.md with the new version and highlights
- Bump version in `src/git_clipboard/__init__.py` and `pyproject.toml`
- Build artifacts

```bash
python -m pip install --upgrade pip build
python -m build
```

- Tag the release and push

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

- If using GitHub Actions publish workflow, create a GitHub Release; the workflow will publish to PyPI using `PYPI_API_TOKEN`


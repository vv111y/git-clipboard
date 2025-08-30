# PyPI Publishing Setup

This repository is configured to automatically publish to PyPI when a GitHub Release is created. To enable this functionality, you need to configure a PyPI API token as a GitHub repository secret.

## Prerequisites

1. A PyPI account with permissions to publish the `git-clipboard` package
2. Maintainer or admin access to this GitHub repository

## Step 1: Create a PyPI API Token

1. Go to [PyPI Account Settings](https://pypi.org/manage/account/)
2. Scroll down to the "API tokens" section
3. Click "Add API token"
4. Choose one of these scopes:
   - **Recommended**: "Scope to project" and select `git-clipboard` (if the project already exists)
   - **Alternative**: "Entire account" (less secure, but works for initial publishing)
5. Give the token a descriptive name like `git-clipboard-github-actions`
6. Click "Add token"
7. **Important**: Copy the token immediately - you won't be able to see it again!

The token will look like: `pypi-AgEIcHlwaS5vcmcCJGxxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx`

## Step 2: Add the Token to GitHub Secrets

1. Go to your GitHub repository: `https://github.com/vv111y/git-clipboard`
2. Click on "Settings" (in the repository menu, not your personal settings)
3. In the left sidebar, click on "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Set the secret details:
   - **Name**: `PYPI_API_TOKEN`
   - **Secret**: Paste the PyPI token you copied in Step 1
6. Click "Add secret"

## Step 3: Verify the Setup

The GitHub Actions workflow (`.github/workflows/publish.yml`) is already configured to use this secret. It will automatically:

1. Trigger when you create a GitHub Release
2. Build the Python package
3. Publish to PyPI using the token

To test the setup:

1. Create a new tag and GitHub Release following the instructions in `CONTRIBUTING.md`
2. The publish workflow should run automatically
3. Check the Actions tab to see if the workflow completes successfully
4. Verify the package appears on PyPI: https://pypi.org/project/git-clipboard/

## Troubleshooting

### Common Issues

**Error: "Invalid or non-existent authentication information"**
- The token may be incorrect or expired
- Regenerate the token on PyPI and update the GitHub secret

**Error: "The user 'USERNAME' isn't allowed to upload to project 'git-clipboard'"**
- Your PyPI account doesn't have permission to publish this package
- Contact the package owner to add you as a maintainer

**Error: "File already exists"**
- You're trying to upload a version that already exists on PyPI
- Bump the version number in `pyproject.toml` and `src/git_clipboard/__init__.py`

### Security Notes

- Never commit PyPI tokens to the repository
- Use project-scoped tokens when possible
- Rotate tokens periodically
- Only trusted maintainers should have access to publishing tokens

## Related Files

- `.github/workflows/publish.yml` - The GitHub Actions workflow that uses this token
- `CONTRIBUTING.md` - Instructions for creating releases that trigger publishing
- `pyproject.toml` - Package configuration including version number
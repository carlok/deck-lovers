# Contributing to deck-lovers

Thanks for helping improve `deck-lovers`.

## Development setup

1. Fork and clone the repository.
2. Create a feature branch.
3. Create local env file:
   ```bash
   cp .env.example .env
   ```
4. Run tests before opening a PR:
   ```bash
   ./run_tests.sh
   ```

## Pull request checklist

- Keep changes focused and small.
- Add/update tests when behavior changes.
- Update `README.md` when CLI, env vars, or workflows change.
- Confirm no secrets are committed (`.env` must stay local).

## Code style

- Python: keep functions focused, typed, and test-covered.
- JavaScript: keep browser logic in small, testable units (`*.pure.js` where possible).
- Prefer explicit naming and clear error messages.

## Commit and PR hygiene

- Use descriptive commit messages (what and why).
- Open PRs against the default branch.
- Include:
  - Problem statement
  - Proposed solution
  - Validation performed

## Reporting bugs

Open an issue with:
- Environment (OS, Docker/Podman version, browser)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs/screenshots

# Contributing to deck-lovers

Thanks for helping improve `deck-lovers`.

Coding agents should read `AGENT.md` for setup, test commands, and repository
conventions. Community standards are in `CODE_OF_CONDUCT.md`.

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
   ./tests/deploy_test.sh   # only if you changed deploy.sh
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

## Security vulnerabilities

Do **not** file public issues for security problems. Follow
[SECURITY.md](SECURITY.md) and use [GitHub private vulnerability
reporting](https://github.com/carlok/deck-lovers/security/advisories/new).

## Reporting bugs

For non-security bugs, open an issue with:
- Environment (OS, Docker/Podman version, browser)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs/screenshots

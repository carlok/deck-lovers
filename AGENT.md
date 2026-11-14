# Agent guide (deck-lovers)

This file is for **coding agents and automated contributors**. Human contributors
should start with `CONTRIBUTING.md` and `README.md`. Keep user-facing docs
general; do not put hostnames, IP addresses, or deployment-specific secrets in
public documentation.

## Repository layout

| Path | Role |
|------|------|
| `converter/` | Markdown/LaTeX → HTML (`md2html.py`, `palette.py`, `emoji_img.py`, `tex_extract.py`); Jest tests for `src/slides.pure.js` |
| `server/` | FastAPI projector/audience server (`server.py`); Jest tests for `src/audience.pure.js` |
| `output/` | Generated slide artifacts (not committed) |
| `palettes/` | Theme JSON consumed by the converter |
| `tests/deploy_test.sh` | Shell tests for `deploy.sh` helpers |
| `docker-compose.yml` | Podman/Docker services for convert, serve, and test profiles |
| `run_tests.sh` | Preferred local test entrypoint (containerized) |

See `ARCHITECTURE.md` for data flow and runtime topology.

## Setup

1. Clone the repo and create a branch off `main`.
2. Copy env template only when running the full stack (not required for unit tests):
   ```bash
   cp .env.example .env
   ```
   Edit `.env` locally; **never commit** `.env`, passwords, API keys, or
   machine-specific paths.
3. **Host dependencies for tests**
   - **Podman** (recommended, matches production docs): `podman` + `podman compose`
   - **Direct on the host** (CI-style, no containers): Python 3.12+, Node 20+

## Running tests

### All suites in containers (canonical locally)

```bash
./run_tests.sh              # all four suites + HTML coverage under test-results/
./run_tests.sh py           # Python only
./run_tests.sh js           # Jest only
./run_tests.sh converter    # converter Python
./run_tests.sh converter-js
./run_tests.sh server       # server Python
./run_tests.sh server-js
./tests/deploy_test.sh      # when deploy.sh or env parsing changes
```

Coverage HTML is written under `test-results/` (`converter/`, `server/`,
`converter-js/`, `server-js/`).

### Host commands (same as CI, no Podman)

**Converter Python** (from repo root):

```bash
python -m pip install --upgrade pip
pip install -r converter/requirements-test.txt
cd converter && pytest tests/ -q \
  --cov=md2html --cov=palette --cov=emoji_img \
  --cov-report=term-missing --cov-fail-under=88
```

**Server Python**:

```bash
pip install -r server/requirements-test.txt
cd server && pytest tests/ -q \
  --cov=server --cov-report=term-missing --cov-fail-under=89
```

**Jest** (each package installs its own devDependencies):

```bash
cd converter && npm ci && npm test -- --ci
cd server && npm ci && npm test -- --ci
```

CI enforces the same coverage floors and publishes summaries in the GitHub Actions
job overview.

## Conventions

- Python: focused functions, type hints where already used, tests beside code
  under `tests/`.
- JavaScript: keep testable logic in `*.pure.js`; browser wiring stays in
  sibling files.
- Do not refactor unrelated product code in tooling or docs PRs.
- Update `README.md` when CLI flags, env vars, or operator workflows change.
- **Before each commit:** run the relevant tests, check coverage did not drop,
  and **prefer adding tests** that increase coverage when you change behavior.
- **Never commit** secrets, tokens, or host-specific values (use `.env` locally
  only).

## Pull requests

- Target the default branch; keep diffs small.
- Use the PR template: problem, solution, validation commands you actually ran.
- License remains **MIT** (`LICENSE`); do not change licensing in drive-by PRs.

## Conduct

Community standards: `CODE_OF_CONDUCT.md`. Enforcement contact:
`carlo.perassi@gmail.com`. Security reports: `SECURITY.md` (not public issues).

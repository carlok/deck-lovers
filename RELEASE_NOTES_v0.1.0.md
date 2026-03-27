# deck-lovers v0.1.0

First public release of `deck-lovers`: interactive presentations with real-time audience feedback.

## Highlights

- Markdown/LaTeX-to-HTML slide pipeline with offline-friendly output.
- FastAPI + WebSocket runtime for projector and audience sync.
- Live audience likes and engagement stats on the presentation side.
- QR-based audience join flow from mobile devices.
- Print/PDF-friendly deck mode for slide download/share.

## Launch hardening included

- CI workflow for Python and JS test suites (`.github/workflows/ci.yml`).
- Security and contributor docs (`SECURITY.md`, `CONTRIBUTING.md`).
- Community health files (issue templates, PR template, `CODEOWNERS`).
- `README` quickstart and launch badges.
- Safer default auth posture (`PROJECTOR_PASSWORD=changeme`).
- Podman-first container workflow for deploy and tests.

## Upgrade notes

- If you previously relied on `PROJECTOR_PASSWORD=admin`, update your `.env`.
- `README` logo path now uses `deck-lovers-logo.png`.

## Validation

- Full test run via containerized workflow:
  - `./run_tests.sh`

## Suggested Git tag

- `v0.1.0`

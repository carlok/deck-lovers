# Security Policy

## Supported versions

This project is currently maintained on the default branch only.

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities.

Report privately to the maintainer:
- GitHub: [@carlok](https://github.com/carlok)

Include:
- Vulnerability description
- Impact assessment
- Reproduction steps or proof of concept
- Suggested mitigation (if available)

## Response target

- Initial acknowledgment: within 7 days
- Triage and remediation timeline: based on severity and exploitability

## Security notes for operators

- Set a strong `PROJECTOR_PASSWORD` in `.env`.
- Keep `PROJECTOR_SECRET` set for public deployments.
- Expose only ports `80/443`; keep internal port `8000` private.
- Never commit `.env`, private keys, or certificates.

# Security Policy

## Supported versions

This project is currently maintained on the default branch only.

## Reporting a vulnerability

Please **do not** open public GitHub issues for security vulnerabilities.

Report them privately using [GitHub private vulnerability reporting](https://github.com/carlok/deck-lovers/security/advisories/new) (repository **Security** tab → **Report a vulnerability**).

Include as much detail as you can:

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
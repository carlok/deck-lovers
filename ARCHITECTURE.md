# Architecture Overview

## Purpose

`deck-lovers` turns Markdown (or extracted LaTeX content) into a standalone slide deck and serves it with real-time audience interaction.

## Main components

- `converter/tex_extract.py`: optional LaTeX Beamer to Markdown extraction.
- `converter/md2html.py`: Markdown to HTML slide deck generator.
- `server/server.py`: FastAPI app for projector, audience, and WebSocket events.
- `server/src/audience.js`: audience-side interaction and like events.
- `deploy.sh`: orchestration for local and remote deployments.

## Data flow

1. Input source:
   - `slides.md` directly, or
   - `source/slides.tex` converted to `output/slides.md`
2. Conversion:
   - `output/slides.md` -> `output/slides.html`
3. Runtime:
   - Projector opens `/`
   - Audience opens `/audience`
   - WebSocket `/ws` propagates `slide_change`, `slide_update`, and `like` events

## Operational notes

- `output/` is generated and mounted read-only into the server container.
- TLS termination is handled by Caddy in `tls` profile.
- Internal app port is `8000`; only `80/443` should be public.

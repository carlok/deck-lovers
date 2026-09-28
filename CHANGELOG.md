# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security
- The projector login cookie now carries a random per-process session token instead of `PROJECTOR_PASSWORD` itself; restarting the server invalidates old cookies. Password and cookie checks are constant-time.

### Added
- `deploy.sh` checks that the host port(s) it is about to publish are free before building, and names the container or process holding them (Podman only reports `"proxy already running"`).

## [0.1.0] - 2026-03-27

### Added
- Initial public release preparation docs and CI scaffolding.

### Changed
- README logo path now uses `deck-lovers-logo.png`.
- Default projector password changed from `admin` to `changeme`.

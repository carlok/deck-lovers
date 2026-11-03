# ── Build stage: install Python deps with pip ────────────────────────────────
# Pinned to bookworm so pip never picks wheels needing a newer glibc than the
# Debian 12 distroless runtime (glibc 2.36).
FROM python:3.11-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --prefix=/install

# ── Runtime: Distroless (no shell, curl, or package manager) ───────────────
# Public gcr.io image — CI and anonymous pulls work without registry auth.
# Optional drop-in: Docker Hardened Images (dhi.io) distroless-compatible tags.
FROM gcr.io/distroless/python3-debian12:nonroot
WORKDIR /app

COPY --from=builder /install /usr/local
# Debian's /usr/bin/python3 only searches dist-packages; point it at the
# site-packages tree that `pip install --prefix` produced.
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
COPY --chown=65532:65532 server.py audience.html ./
COPY --chown=65532:65532 src/ ./src/

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD ["/usr/bin/python3", "server.py", "healthcheck"]
CMD ["-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

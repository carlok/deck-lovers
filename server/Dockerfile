FROM python:3.11-slim
WORKDIR /app

# Drop privileges — run as non-root (UID/GID 1000)
RUN addgroup --system --gid 1000 appuser \
 && adduser  --system --uid 1000 --ingroup appuser --no-create-home appuser

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser server.py .
COPY --chown=appuser:appuser audience.html .

USER appuser
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

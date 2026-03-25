FROM python:3.11-slim
WORKDIR /app

# Drop privileges — run as non-root (UID/GID 1000)
RUN addgroup --system --gid 1000 appuser \
 && adduser  --system --uid 1000 --ingroup appuser --no-create-home appuser

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser tex_extract.py .
COPY --chown=appuser:appuser md2html.py .

USER appuser

CMD ["python", "md2html.py", \
     "--input",  "/workspace/slides.md", \
     "--output", "/workspace/slides.html"]

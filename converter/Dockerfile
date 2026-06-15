FROM python:3.11-slim
WORKDIR /app

# Converters run as root — they are ephemeral batch jobs with no network ports.
# They only touch the explicitly-mounted /workspace volume, so UID alignment
# with the host is the only thing that matters (handled by convert.sh / --setup).
# Non-root is enforced on the long-running server container instead.

COPY converter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY converter/tex_extract.py converter/md2html.py converter/palette.py ./
COPY palettes/ ./palettes/

CMD ["python", "md2html.py", \
     "--input",  "/workspace/slides.md", \
     "--output", "/workspace/slides.html"]

FROM python:3.13-slim

# Avoid writing bytecode and ensure logs flush straight to stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies
RUN pip install --no-cache-dir \
    fastmcp>=2.12.4 \
    httpx>=0.28.1 \
    "mcp[cli]>=1.16.0"

# Copy application source
COPY . /app

EXPOSE 8000

# Defaults to HTTP transport so the container can accept inbound connections
ENTRYPOINT ["fastmcp", "run", "server.py:mcp"]

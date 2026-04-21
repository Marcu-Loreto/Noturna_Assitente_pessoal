FROM python:3.13-slim

WORKDIR /app

# Install system deps (openssl for certs, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY noturna_client.py noturna_agent.py mcp_bridge.py whatsapp_bridge.py ./
COPY prompts/ prompts/

# Create dirs for runtime data
RUN mkdir -p data logs .certs

EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl -k https://localhost:8443/ || exit 1

CMD ["uv", "run", "python", "noturna_client.py"]

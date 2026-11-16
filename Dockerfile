# syntax=docker/dockerfile:1.7

ARG NODE_VERSION=24.22.1
ARG PYTHON_VERSION=3.12.16
ARG FILESYSTEM_MCP_VERSION=2.3.0

FROM node:${NODE_VERSION}-bookworm-slim AS filesystem-mcp

ARG FILESYSTEM_MCP_VERSION
RUN npm install --omit=dev \
        --prefix /opt/filesystem-mcp \
        "@modelcontextprotocol/server-filesystem@${FILESYSTEM_MCP_VERSION}" \
    && npm cache clean --force

FROM node:${NODE_VERSION}-bookworm-slim AS frontend-build

WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="TenderGuard Africa" \
      org.opencontainers.image.description="Self-hosted procurement decision-support agent" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TENDERGUARD_FILESYSTEM_MCP_COMMAND="/opt/filesystem-mcp/node_modules/.bin/mcp-server-filesystem"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --requirement /tmp/requirements.lock \
    && rm /tmp/requirements.lock

COPY --from=filesystem-mcp /usr/local/bin/node /usr/local/bin/node
COPY --from=filesystem-mcp /opt/filesystem-mcp /opt/filesystem-mcp

RUN groupadd --system --gid 10001 tenderguard \
    && useradd --system --uid 10001 --gid tenderguard \
        --home-dir /home/tenderguard --create-home tenderguard

WORKDIR /app

COPY --chown=tenderguard:tenderguard app ./app
COPY --chown=tenderguard:tenderguard mcp_servers ./mcp_servers
COPY --chown=tenderguard:tenderguard data ./data
COPY --from=frontend-build --chown=tenderguard:tenderguard /src/frontend/dist ./frontend/dist
COPY --chown=tenderguard:tenderguard pyproject.toml README.md LICENSE ./

RUN mkdir --parents /app/reports /app/storage \
    && chown tenderguard:tenderguard /app/reports /app/storage

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()"]

CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]

FROM python:3.13-slim

WORKDIR /app

RUN groupadd --system app && useradd --system --uid 1000 --gid app --home-dir /app app

COPY src/ops-mcp/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY src/ops-mcp/server.py ./server.py
COPY src/ops-mcp/write_server.py ./write_server.py
COPY src/ops-mcp/connectors ./connectors

RUN chown -R app:app /app
USER app

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health')"

CMD ["python", "server.py"]

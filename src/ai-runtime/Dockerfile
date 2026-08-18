FROM python:3.13-slim
WORKDIR /app
COPY src/ai-runtime/pyproject.toml .
RUN pip install --no-cache-dir '.[dev]'
COPY src/ai-runtime/ .
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
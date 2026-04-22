FROM python:3.12-slim

WORKDIR /app

# Install Python agent dependencies + web dependencies
COPY python/pyproject.toml python/pyproject.toml
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic httpx

# Copy Python agent source
COPY python/src /app/python/src

# Copy web app
COPY web /app/web

ENV PYTHONPATH=/app/python/src
WORKDIR /app/web

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

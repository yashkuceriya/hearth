FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "." && pip install grpcio-health-checking grpcio-reflection
COPY . .

FROM python:3.12-slim
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
USER appuser
EXPOSE 50053 50054 8082 8083
ENTRYPOINT ["python3", "-m", "server"]

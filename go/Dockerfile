FROM golang:1.23-alpine AS builder
RUN apk add --no-cache git
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /orchestrator ./cmd/orchestrator

FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata && \
    adduser -D -u 1000 appuser
COPY --from=builder /orchestrator /usr/local/bin/orchestrator
COPY migrations/ /app/migrations/
USER appuser
EXPOSE 50051 8080
HEALTHCHECK --interval=10s --timeout=3s CMD ["/usr/local/bin/orchestrator", "-health"] || exit 1
ENTRYPOINT ["orchestrator"]

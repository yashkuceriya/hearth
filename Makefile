.PHONY: proto setup test lint build docker-up docker-down migrate

# === Per-Language Targets ===
go-build:
	cd go && go build ./...

go-test:
	cd go && go test ./... -race -count=1

go-lint:
	cd go && golangci-lint run

ruby-test:
	cd ruby && bundle exec rspec

ruby-lint:
	cd ruby && bundle exec rubocop

python-test:
	cd python && python -m pytest tests/ -v

python-lint:
	cd python && ruff check src/ tests/
	cd python && mypy src/

# === Aggregate ===
test: go-test ruby-test python-test
lint: go-lint ruby-lint python-lint
build: go-build

# === Docker ===
docker-up:
	cd deploy && docker compose up -d

docker-down:
	cd deploy && docker compose down

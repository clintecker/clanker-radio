.PHONY: help sync-db tui build-tui clean test

help: ## Show this help message
	@echo "LAST BYTE RADIO - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

sync-db: ## Sync database from production server
	@./scripts/sync_db.sh

tui: sync-db ## Sync database and run the TUI
	@go run ./cmd/radiotui

build-tui: ## Build the TUI binary
	@echo "🔨 Building radiotui..."
	@go build -o bin/radiotui ./cmd/radiotui
	@echo "✅ Binary created at bin/radiotui"

clean: ## Clean build artifacts
	@rm -rf bin/
	@echo "✅ Cleaned build artifacts"

test: ## Run tests
	@uv run pytest tests/ -v

.DEFAULT_GOAL := help

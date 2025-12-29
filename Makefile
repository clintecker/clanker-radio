# Production server connection
SERVER = clint@10.10.0.86
REMOTE_BASE = /srv/ai_radio

.PHONY: help sync-db tui build-tui clean test
.PHONY: deploy deploy-frontend deploy-scripts deploy-code
.PHONY: status logs-liquidsoap logs-push logs-break-gen logs-station-id
.PHONY: check-exports test-sse check-db check-callbacks now-playing
.PHONY: restart-liquidsoap restart-push restart-all tail-all

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

# --- Server Operations (10.10.0.86) ---

deploy: ## Deploy all (frontend + scripts + code)
	@./scripts/deploy.sh lastbyte all

deploy-frontend: ## Deploy frontend only
	@./scripts/deploy.sh lastbyte frontend

deploy-scripts: ## Deploy Python scripts only
	@./scripts/deploy.sh lastbyte scripts

deploy-code: ## Deploy ai_radio package only
	@./scripts/deploy.sh lastbyte code

status: ## Show all service statuses
	@ssh $(SERVER) "systemctl list-units 'ai-radio-*' --no-pager"

logs-liquidsoap: ## Tail Liquidsoap logs (callbacks, tracks)
	@ssh $(SERVER) "tail -f $(REMOTE_BASE)/logs/liquidsoap.log"

logs-push: ## Tail SSE push daemon logs
	@ssh $(SERVER) "sudo journalctl -u ai-radio-push.service -f"

logs-break-gen: ## Show break-gen service logs
	@ssh $(SERVER) "sudo journalctl -u ai-radio-break-gen.service -n 50"

logs-station-id: ## Show station-id service logs
	@ssh $(SERVER) "sudo journalctl -u ai-radio-station-id.service -n 50"

check-exports: ## Show recent export script logs
	@ssh $(SERVER) "ls -lt /tmp/ai_radio_logs/export_*.out 2>/dev/null | head -5 && echo '---' && tail -20 /tmp/ai_radio_logs/export_*.out 2>/dev/null | head -40"

test-sse: ## Manually trigger SSE notification
	@echo "Triggering SSE notification..."
	@ssh $(SERVER) "curl -X POST http://127.0.0.1:8001/notify"
	@echo "\nCheck logs-push to verify broadcast"

check-db: ## Verify database file and permissions
	@ssh $(SERVER) "ls -lh $(REMOTE_BASE)/db/*.sqlite3 $(REMOTE_BASE)/db/*.db 2>/dev/null"

check-callbacks: ## Check if callbacks are firing
	@ssh $(SERVER) "grep -A 15 'CALLBACK FIRED' $(REMOTE_BASE)/logs/liquidsoap.log | tail -40"

now-playing: ## Show current now_playing.json
	@ssh $(SERVER) "cat $(REMOTE_BASE)/public/now_playing.json | python3 -m json.tool"

restart-liquidsoap: ## Restart Liquidsoap service
	@ssh $(SERVER) "sudo systemctl restart ai-radio-liquidsoap.service"
	@echo "Liquidsoap restarted"

restart-push: ## Restart SSE push daemon
	@ssh $(SERVER) "sudo systemctl restart ai-radio-push.service"
	@echo "SSE push daemon restarted"

restart-all: ## Restart all services
	@ssh $(SERVER) "sudo systemctl restart ai-radio-liquidsoap.service ai-radio-push.service"
	@echo "All services restarted"

tail-all: ## Quick check of all logs
	@echo "=== Liquidsoap (last 10 lines) ==="
	@ssh $(SERVER) "tail -10 $(REMOTE_BASE)/logs/liquidsoap.log"
	@echo ""
	@echo "=== SSE Push (last 10 lines) ==="
	@ssh $(SERVER) "sudo journalctl -u ai-radio-push.service -n 10 --no-pager"

check-export-stderr: ## Check stderr from recent export attempts
	@ssh $(SERVER) "ls -lt /tmp/ai_radio_logs/export_*.err 2>/dev/null | head -5 && echo '---' && for f in \$$(ls -t /tmp/ai_radio_logs/export_*.err 2>/dev/null | head -3); do echo \"=== \$$f ===\"tail -20 \"\$$f\" 2>/dev/null || echo 'empty'; done"

check-lock-file: ## Check export lock file ownership
	@ssh $(SERVER) "ls -la /tmp/export_now_playing.lock 2>/dev/null || echo 'Lock file does not exist'"

check-process-output: ## Check recent record_play process outputs from Liquidsoap
	@ssh $(SERVER) "grep 'Process stdout.*PID' $(REMOTE_BASE)/logs/liquidsoap.log | tail -5"

check-sse-broadcasts: ## Check recent SSE broadcast times
	@ssh $(SERVER) "sudo journalctl -u ai-radio-push.service --since '1 hour ago' --no-pager | grep 'Broadcasting update'"

watch-callbacks: ## Monitor for next track change and export (live tail)
	@ssh $(SERVER) "tail -f $(REMOTE_BASE)/logs/liquidsoap.log | grep --line-buffered -E '(CALLBACK FIRED|Calling export_now_playing|Export and SSE notification)'"

.DEFAULT_GOAL := help

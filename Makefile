# Production server connection
SERVER = clint@10.10.0.86
REMOTE_BASE = /srv/ai_radio

.PHONY: help sync-db tui build-tui clean test
.PHONY: deploy deploy-frontend deploy-scripts deploy-code
.PHONY: status logs-liquidsoap logs-push logs-break-gen logs-station-id
.PHONY: check-exports test-sse check-db check-callbacks now-playing
.PHONY: restart-liquidsoap restart-push restart-all tail-all
.PHONY: check-station-ids status-station-id logs-station-id-timer check-last-station-id

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

check-station-ids: ## Show station IDs in database
	@ssh $(SERVER) "sqlite3 $(REMOTE_BASE)/db/radio.sqlite3 'SELECT COUNT(*) as count FROM assets WHERE kind=\"bumper\"; SELECT id, title, artist, path FROM assets WHERE kind=\"bumper\" LIMIT 5;'"

status-station-id: ## Show station-id service and timer status
	@ssh $(SERVER) "systemctl status ai-radio-station-id.service ai-radio-station-id.timer --no-pager"

logs-station-id-timer: ## Show recent station-id timer activations
	@ssh $(SERVER) "sudo journalctl -u ai-radio-station-id.timer -n 20 --no-pager"

check-last-station-id: ## Show last 10 station IDs played
	@ssh $(SERVER) "sqlite3 $(REMOTE_BASE)/db/radio.sqlite3 'SELECT datetime(ph.played_at, \"localtime\") as played, a.title, a.artist FROM play_history ph JOIN assets a ON ph.asset_id = a.id WHERE a.kind=\"bumper\" ORDER BY ph.played_at DESC LIMIT 10;'"

# --- Sacred Callback Debugging Incantations ---

recent-plays: ## Show last 10 plays from database with timestamps
	@ssh $(SERVER) "sqlite3 $(REMOTE_BASE)/db/radio.sqlite3 'SELECT datetime(ph.played_at, \"localtime\") as time, a.title, a.artist, ph.source FROM play_history ph JOIN assets a ON ph.asset_id = a.id ORDER BY ph.played_at DESC LIMIT 10'"

callback-logs: ## Show recent callback executions
	@ssh $(SERVER) "sudo journalctl -u ai-radio-liquidsoap.service -n 100 --no-pager | grep -E 'MUSIC QUEUED|BREAK START|BUMPER START|TRACK START|SUCCESS|ERROR|CALLBACK'"

callback-timing: ## Check callback timing accuracy
	@ssh $(SERVER) "sudo journalctl -u ai-radio-liquidsoap.service -n 200 --no-pager | grep -E 'QUEUED|TRACK START' | tail -20"

watch-callbacks-live: ## Live monitor of callback execution
	@ssh $(SERVER) "sudo journalctl -u ai-radio-liquidsoap.service -f | grep --line-buffered -E 'MUSIC|BREAK|BUMPER|SUCCESS|ERROR'"

verify-sync: ## Compare database vs Icecast metadata timing
	@echo "=== Last 5 Database Entries ==="
	@ssh $(SERVER) "sqlite3 $(REMOTE_BASE)/db/radio.sqlite3 'SELECT datetime(played_at, \"localtime\"), title FROM play_history ph JOIN assets a ON ph.asset_id = a.id ORDER BY played_at DESC LIMIT 5'"
	@echo ""
	@echo "=== Last 5 Icecast Metadata Updates ==="
	@ssh $(SERVER) "sudo tail -100 /var/log/icecast2/error.log | grep 'Metadata.*changed to' | tail -5 | sed 's/.*Metadata on mountpoint.*changed to //'"

.DEFAULT_GOAL := help

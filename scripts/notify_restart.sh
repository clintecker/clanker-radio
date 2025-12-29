#!/bin/bash
# Notify SSE clients that a service is restarting
# Called by systemd ExecStop before stopping services

SERVICE_NAME="$1"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name>"
    exit 1
fi

# Build shutdown message
MESSAGE=$(cat <<EOF
{
  "system_status": "restarting",
  "message": "$SERVICE_NAME restarting - reconnecting shortly..."
}
EOF
)

# POST to push daemon's /notify endpoint
# Use short timeout to avoid hanging shutdown
curl -X POST \
     -H "Content-Type: application/json" \
     -d "$MESSAGE" \
     --max-time 2 \
     http://127.0.0.1:8001/notify \
     2>/dev/null

exit 0

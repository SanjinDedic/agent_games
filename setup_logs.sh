#!/bin/bash
set -euo pipefail

cat <<'EOF'
This project no longer uses bind-mounted log files.

- Services now log to stdout/stderr and are captured by Docker's logging driver.
- View logs with:  docker compose logs -f [service]
- On Linux hosts you can switch to journald by running with LOG_DRIVER=journald.
  Example: LOG_DRIVER=journald docker compose up
- On macOS/Windows (Docker Desktop), journald is not supported; the compose defaults to the 'local' driver.

This script is deprecated and does nothing now.
EOF

exit 0
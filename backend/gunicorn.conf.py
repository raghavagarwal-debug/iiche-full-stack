"""
Gunicorn configuration for production deployment.
Per Section 10: multiple workers to approach the 500 RPS target.

Worker count is configurable via the WEB_CONCURRENCY env var.
Default: 4 workers (suitable for a 2-core machine).
"""

import os

# --- Workers ---
# Each worker runs its own event loop and DB/Redis connection pool.
# Rule of thumb: 2 × CPU cores + 1 for I/O-bound apps.
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
worker_class = "uvicorn.workers.UvicornWorker"

# --- Binding ---
bind = os.environ.get("BIND", "0.0.0.0:8000")

# --- Timeouts ---
timeout = 120           # Kill workers that take longer than this
graceful_timeout = 30   # Time for graceful shutdown
keepalive = 5           # Seconds to wait for keep-alive connections

# --- Memory Leak Protection ---
# Restart workers after this many requests to prevent slow memory leaks.
max_requests = 1000
max_requests_jitter = 100  # Randomize to avoid all workers restarting at once

# --- Logging ---
accesslog = "-"         # Log to stdout
errorlog = "-"          # Log to stderr
loglevel = os.environ.get("LOG_LEVEL", "info")

# --- Preloading ---
# Preload app to share memory between workers (copy-on-write).
# Disable if using --reload in development.
preload_app = os.environ.get("PRELOAD_APP", "true").lower() == "true"

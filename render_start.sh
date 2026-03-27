#!/bin/bash
# Sentinel Shield v2 — Production Render Startup Script
# Professional launch wrapper for 512MB RAM constraints

# 1. Ensure current directory (backend) is in the Python Path
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/backend

# 2. Set Memory Optimizations
export WEB_CONCURRENCY=1
export PYTHONUNBUFFERED=1

# 3. Launch with Gunicorn (Harder, Faster, Leaner)
# Using 1 worker and 4 threads to provide concurrency without a RAM explosion.
exec gunicorn -w 1 -k uvicorn.workers.UvicornWorker backend.app:app --host 0.0.0.0 --port $PORT --timeout 120

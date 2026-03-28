#!/bin/bash
# Sentinel Shield v2 — Production Render Startup Script
# Professional launch wrapper for 512MB RAM constraints

# 1. Ensure current directory (backend) is in the Python Path
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/backend

# 2. Set Memory Optimizations
export WEB_CONCURRENCY=1
export PYTHONUNBUFFERED=1

# 3. Launch with Gunicorn (Harder, Faster, Leaner)
# Using 1 worker and 1 thread to minimize RAM (Render free tier)
exec gunicorn -w 1 -k uvicorn.workers.UvicornWorker backend.app:app -b 0.0.0.0:$PORT --timeout 120

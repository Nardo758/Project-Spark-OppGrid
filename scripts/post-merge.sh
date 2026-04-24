#!/bin/bash
set -e

echo "=== OppGrid post-merge setup ==="

# Install / sync backend Python dependencies
echo "--- Installing backend dependencies ---"
pip install -r backend/requirements-replit.txt --quiet

# Install / sync frontend Node dependencies
echo "--- Installing frontend dependencies ---"
cd frontend && npm install --silent && cd ..

# Run any pending Alembic migrations
echo "--- Running database migrations ---"
cd backend && PYTHONPATH=. alembic upgrade head && cd ..

echo "=== Post-merge setup complete ==="

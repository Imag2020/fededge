#!/bin/bash
set -e

cd /app
echo "🚀 Starting FedEdge..."

# 1. LLAMA (9001 chat + 9002 embeddings)
echo "🤖 Starting llama-server with BLAS optimization..."
./start_llamacpp.sh &

# Attendre que les serveurs llama.cpp soient prêts
echo "⏳ Waiting for llama.cpp servers to be ready..."
sleep 15

# Vérifier que les serveurs sont bien démarrés
if curl -fsS http://127.0.0.1:9001/health >/dev/null 2>&1 || \
   curl -fsS http://127.0.0.1:9001/v1/models >/dev/null 2>&1; then
    echo "✅ Chat server (9001) is ready"
else
    echo "⚠️  Chat server (9001) not responding, but continuing..."
fi

if curl -fsS http://127.0.0.1:9002/health >/dev/null 2>&1 || \
   curl -fsS http://127.0.0.1:9002/v1/models >/dev/null 2>&1; then
    echo "✅ Embeddings server (9002) is ready"
else
    echo "⚠️  Embeddings server (9002) not responding, but continuing..."
fi

# 2. API + WEBSOCKET
echo "🌐 Starting FastAPI application..."
. /app/venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000

wait
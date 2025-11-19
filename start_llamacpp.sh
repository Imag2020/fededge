#!/usr/bin/env bash
set -euo pipefail

# === Config par défaut (modifiable via variables d'env) ======================
BIN_DEFAULT="./bin/llama-server"

#CHAT_MODEL_DEFAULT="./models/gemma-3-1b-it-Q4_1.gguf"
#CHAT_MODEL_DEFAULT="./models/unsloth_Qwen3-4B-Instruct-2507-GGUF_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
CHAT_MODEL_DEFAULT="./models/unsloth_gemma-3-4b-it-GGUF_gemma-3-4b-it-Q4_K_M.gguf"
CHAT_PORT_DEFAULT="${CHAT_PORT:-9001}"

EMB_MODEL_DEFAULT="./models/unsloth_embeddinggemma-300m-GGUF_embeddinggemma-300M-Q8_0.gguf"
EMB_PORT_DEFAULT="${EMB_PORT:-9002}"

# Timeout (secondes) pour l'attente de disponibilité HTTP
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-1}"

# === Dossiers =================================================================
DATA_DIR="${DATA_DIR:-./data}"
LOG_DIR="$DATA_DIR/logs"
LOG_CHAT="$LOG_DIR/chat.log"
LOG_EMB="$LOG_DIR/embeddings.log"
RUN_DIR="./bin/"

# Créer les dossiers si nécessaire
mkdir -p "$LOG_DIR"

# === Fonctions utilitaires ====================================================
ts() { date +"%Y-%m-%d %H:%M:%S"; }
die(){ echo "[$(ts)] ❌ $*" >&2; exit 1; }
info(){ echo "[$(ts)] $*"; }

health_check() {
  local port="$1"
  local deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
  while (( $(date +%s) < deadline )); do
    if curl -fsS "http://127.0.0.1:${port}/health"   >/dev/null 2>&1; then return 0; fi
    if curl -fsS "http://127.0.0.1:${port}/healthz"  >/dev/null 2>&1; then return 0; fi
    if curl -fsS "http://127.0.0.1:${port}/version"  >/dev/null 2>&1; then return 0; fi
    if curl -fsS "http://127.0.0.1:${port}/v1/models" >/dev/null 2>&1; then return 0; fi
    sleep "$HEALTH_INTERVAL"
  done
  return 1
}

start_server() {
  local name="$1"
  local bin="$2"
  local model="$3"
  local port="$4"
  local extra_args="${5:-}"

  [[ -x "$bin" ]]   || die "binaire introuvable/non exécutable: $bin"
  [[ -r "$model" ]] || die "modèle introuvable: $model"

  local log="${LOG_DIR}/${name}.log"
  local pidfile="${RUN_DIR}/${name}.pid"

  if [[ -f "$pidfile" ]]; then
    local oldpid; oldpid="$(cat "$pidfile" || true)"
    if [[ -n "${oldpid}" ]] && ps -p "${oldpid}" >/dev/null 2>&1; then
      info "🔁 ${name}: déjà lancé (pid=${oldpid}), vérification…"
      if health_check "$port"; then
        info "✅ ${name}: OK (port=${port})"
        return 0
      else
        info "⚠️  ${name}: relance…"; kill "${oldpid}" || true; sleep 1
      fi
    fi
  fi

  info "🚀 lancement ${name}: $bin -m $model --port $port --host 127.0.0.1 $extra_args"
  nohup "$bin" -m "$model" --port "$port" --host 127.0.0.1 $extra_args >>"$log" 2>&1 &
  local pid=$!
  echo "$pid" > "$pidfile"
  info "⏳ ${name}: pid=${pid}, log=${log} ; attente…"

  if health_check "$port"; then
    info "✅ ${name}: prêt sur http://127.0.0.1:${port}"

    # Test JSON pour le serveur chat
    if [[ "$name" == "chat" ]]; then
      info "🧪 ${name}: test JSON non-streamé..."
      if curl -fsS -H "Content-Type: application/json" \
          -d '{"model":"local","stream":false,"max_tokens":50,"messages":[{"role":"user","content":"Say hello."}]}' \
          "http://127.0.0.1:${port}/v1/chat/completions" >/dev/null 2>&1; then
        info "✅ ${name}: réponse JSON non-stream OK"
      else
        info "⚠️ ${name}: test JSON a échoué (non-fatal)"
      fi
    fi
  else
    info "📄 Dernières lignes du log ${name}:"; tail -n 60 "$log" || true
    die "${name}: indisponible après ${HEALTH_TIMEOUT}s (port=${port})"
  fi
}

# === Paramètres effectifs =====================================================
BIN="${LLAMA_BIN:-$BIN_DEFAULT}"

CHAT_MODEL="${LLAMA_CHAT_MODEL:-$CHAT_MODEL_DEFAULT}"
CHAT_PORT="${CHAT_PORT:-$CHAT_PORT_DEFAULT}"

EMB_MODEL="${LLAMA_EMB_MODEL:-$EMB_MODEL_DEFAULT}"
EMB_PORT="${EMB_PORT:-$EMB_PORT_DEFAULT}"

# === Lancements ===============================================================
# Chat server : commande minimale qui fonctionne
start_server "chat" "$BIN" "$CHAT_MODEL" "$CHAT_PORT" ""

# Embeddings server : on active le mode embeddings
start_server "embeddings" "$BIN" "$EMB_MODEL" "$EMB_PORT" "--embedding"

info "🎉 Les deux serveurs sont UP."
info "   - Chat      : http://127.0.0.1:${CHAT_PORT}"
info "   - Embeddings: http://127.0.0.1:${EMB_PORT}"


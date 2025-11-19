#!/usr/bin/env bash
set -euo pipefail

# === Config (modifiable via variables d'env) ==============================
RUN_DIR="./run"
LOG_DIR="./logs"

CHAT_NAME="${CHAT_NAME:-chat}"
EMB_NAME="${EMB_NAME:-embeddings}"

CHAT_PORT="${CHAT_PORT:-9001}"
EMB_PORT="${EMB_PORT:-9002}"

TERM_TIMEOUT="${TERM_TIMEOUT:-20}"    # secondes à attendre après SIGTERM
PORT_TIMEOUT="${PORT_TIMEOUT:-15}"    # secondes pour que le port se libère

# === Utils ================================================================
ts() { date +"%Y-%m-%d %H:%M:%S"; }
info(){ echo "[$(ts)] $*"; }
warn(){ echo "[$(ts)] ⚠️  $*" >&2; }
err(){  echo "[$(ts)] ❌ $*" >&2; }

is_alive() {
  local pid="$1"
  [[ -n "${pid:-}" ]] && ps -p "$pid" >/dev/null 2>&1
}

pids_listening_on_port() {
  local port="$1"
  # Retourne des PIDs (peut nécessiter sudo selon système)
  # On essaie ss puis lsof en fallback.
  if command -v ss >/dev/null 2>&1; then
    # extrait pids du style users:(("server",pid=1234,fd=...))
    ss -ltnp "sport = :$port" 2>/dev/null \
      | awk -F',' '/users:\(\("/ { for(i=1;i<=NF;i++){ if($i ~ /pid=/){ sub(/pid=/,"",$i); gsub(/\).*/,"",$i); print $i } } }' \
      | sort -u
  elif command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN -Fp 2>/dev/null | sed -n 's/^p//p' | sort -u
  else
    return 0
  fi
}

wait_for_exit() {
  local pid="$1" timeout="$2"
  local end=$(( $(date +%s) + timeout ))
  while (( $(date +%s) < end )); do
    if ! is_alive "$pid"; then return 0; fi
    sleep 1
  done
  return 1
}

wait_port_freed() {
  local port="$1" timeout="$2"
  local end=$(( $(date +%s) + timeout ))
  while (( $(date +%s) < end )); do
    if ! ss -ltn "sport = :$port" | grep -q ":$port"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_one() {
  local name="$1" port="$2"

  local pidfile="${RUN_DIR}/${name}.pid"
  local had_pidfile=false
  local pids=()

  if [[ -f "$pidfile" ]]; then
    had_pidfile=true
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "$pid" ]]; then
      pids+=("$pid")
    fi
  fi

  # Si pas de PIDfile ou process déjà mort, tente par PORT
  if [[ ${#pids[@]} -eq 0 ]]; then
    mapfile -t pids < <(pids_listening_on_port "$port")
  fi

  if [[ ${#pids[@]} -eq 0 ]]; then
    info "ℹ️  ${name}: aucun process détecté (pidfile=${had_pidfile}, port=${port})."
    [[ -f "$pidfile" ]] && rm -f "$pidfile"
    return 0
  fi

  info "🛑 Arrêt ${name}: PIDs=${pids[*]} (port=${port})"

  # SIGTERM gracieux
  for pid in "${pids[@]}"; do
    if is_alive "$pid"; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  # Attente
  local all_stopped=true
  for pid in "${pids[@]}"; do
    if is_alive "$pid"; then
      if ! wait_for_exit "$pid" "$TERM_TIMEOUT"; then
        warn "${name}: pid ${pid} ne s'arrête pas (TERM). Envoi SIGKILL…"
        kill -KILL "$pid" 2>/dev/null || true
        # petite attente post-KILL
        sleep 1
        if is_alive "$pid"; then
          err "${name}: pid ${pid} encore vivant après KILL."
          all_stopped=false
        fi
      fi
    fi
  done

  # Nettoyage pidfile si plus aucun process
  if $all_stopped; then
    [[ -f "$pidfile" ]] && rm -f "$pidfile"
  fi

  # Vérifier libération du port
  if wait_port_freed "$port" "$PORT_TIMEOUT"; then
    info "✅ ${name}: port ${port} libéré."
  else
    warn "⏳ ${name}: le port ${port} semble encore occupé après ${PORT_TIMEOUT}s."
    ss -ltnp "sport = :$port" || true
  fi
}

main() {
  mkdir -p "$RUN_DIR" "$LOG_DIR"

  stop_one "$CHAT_NAME" "$CHAT_PORT"
  stop_one "$EMB_NAME"  "$EMB_PORT"

  info "✔️  Arrêt demandé pour les deux serveurs."
}

main "$@"


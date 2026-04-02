#!/usr/bin/env bash
set -euo pipefail

SSR_BRANCH="${SSR_BRANCH:-ServerStatus-Rabbit-NG}"
SSR_REPO_URL="${SSR_REPO_URL:-https://github.com/wingsrabbit/ServerStatus-Rabbit.git}"
SSR_APP_DIR="${SSR_APP_DIR:-/opt/ServerStatus-Rabbit}"
SSR_IMAGE="${SSR_IMAGE:-serverstatus-rabbit:v0.131}"
SSR_CONTAINER="${SSR_CONTAINER:-ssr-server}"
SSR_WEB_PORT="${SSR_WEB_PORT:-9191}"
SSR_TCP_PORT="${SSR_TCP_PORT:-9192}"
SSR_UI_HEADER="${SSR_UI_HEADER:-ServerStatus-Rabbit v0.131}"
SSR_UI_SUBHEADER="${SSR_UI_SUBHEADER:-Server probes set up with ServerStatus-Rabbit}"

log() {
  printf "[install-server] %s\n" "$*"
}

fail() {
  printf "[install-server] %s\n" "$*" >&2
  exit 1
}

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    fail "please run this installer as root"
  fi
}

install_pkg() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y "$@"
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y "$@"
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    yum install -y "$@"
    return
  fi
  fail "unsupported package manager, install required dependencies manually"
}

ensure_git() {
  if ! command -v git >/dev/null 2>&1; then
    log "git not found, installing git"
    install_pkg git
  fi
}

ensure_docker() {
  if ! command -v curl >/dev/null 2>&1; then
    log "curl not found, installing curl"
    install_pkg curl
  fi

  if ! command -v docker >/dev/null 2>&1; then
    log "docker not found, installing docker"
    if command -v apt-get >/dev/null 2>&1; then
      if ! install_pkg docker.io; then
        log "package install failed, falling back to get.docker.com"
        curl -fsSL https://get.docker.com | sh
      fi
    elif command -v dnf >/dev/null 2>&1; then
      if ! dnf install -y docker; then
        log "package install failed, falling back to get.docker.com"
        curl -fsSL https://get.docker.com | sh
      fi
    elif command -v yum >/dev/null 2>&1; then
      if ! yum install -y docker; then
        log "package install failed, falling back to get.docker.com"
        curl -fsSL https://get.docker.com | sh
      fi
    else
      curl -fsSL https://get.docker.com | sh
    fi
  fi

  if command -v systemctl >/dev/null 2>&1; then
    systemctl enable --now docker >/dev/null 2>&1 || true
  elif command -v service >/dev/null 2>&1; then
    service docker start >/dev/null 2>&1 || true
  fi

  if ! docker info >/dev/null 2>&1; then
    fail "docker daemon is not available after installation"
  fi
}

sync_repo() {
  if [ -d "$SSR_APP_DIR/.git" ]; then
    log "updating existing repo in $SSR_APP_DIR"
    git -C "$SSR_APP_DIR" fetch origin "$SSR_BRANCH:refs/remotes/origin/$SSR_BRANCH"
    git -C "$SSR_APP_DIR" checkout -B "$SSR_BRANCH" "origin/$SSR_BRANCH"
    git -C "$SSR_APP_DIR" pull --ff-only origin "$SSR_BRANCH"
    return
  fi

  log "cloning $SSR_REPO_URL#$SSR_BRANCH into $SSR_APP_DIR"
  rm -rf "$SSR_APP_DIR"
  git clone -b "$SSR_BRANCH" "$SSR_REPO_URL" "$SSR_APP_DIR"
}

sync_settings() {
  local pycode

  mkdir -p "$SSR_APP_DIR/data"
  log "syncing settings.json with selected ports"
  pycode="import json, os; from pathlib import Path; p = Path('/data/settings.json'); settings = json.loads(p.read_text()) if p.exists() else {}; settings.setdefault('https', {'enabled': False, 'mode': 'letsencrypt', 'domain': '', 'email': '', 'cert_path': '', 'key_path': ''}); settings.setdefault('ports', {}); settings['ports']['web'] = int(os.environ['SSR_WEB_PORT']); settings['ports']['tcp'] = int(os.environ['SSR_TCP_PORT']); settings['ports'].setdefault('https', 443); settings['ports'].setdefault('web_enabled', True); settings['ports'].setdefault('https_enabled', False); settings.setdefault('webhook', {'enabled': False, 'url': '', 'timeout_seconds': 30}); settings.setdefault('ui', {}); settings['ui']['header'] = os.environ['SSR_UI_HEADER']; settings['ui']['subHeader'] = os.environ['SSR_UI_SUBHEADER']; p.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n')"
  docker run --rm \
    -e SSR_WEB_PORT="$SSR_WEB_PORT" \
    -e SSR_TCP_PORT="$SSR_TCP_PORT" \
    -e SSR_UI_HEADER="$SSR_UI_HEADER" \
    -e SSR_UI_SUBHEADER="$SSR_UI_SUBHEADER" \
    -v "$SSR_APP_DIR/data:/data" \
    python:3.12-slim \
    python -c "$pycode"
}

build_image() {
  log "building image $SSR_IMAGE"
  docker build -t "$SSR_IMAGE" "$SSR_APP_DIR"
}

run_container() {
  log "starting container $SSR_CONTAINER"
  docker rm -f "$SSR_CONTAINER" >/dev/null 2>&1 || true
  docker run -d --restart=always \
    --name "$SSR_CONTAINER" \
    -p "$SSR_WEB_PORT:$SSR_WEB_PORT" \
    -p "$SSR_TCP_PORT:$SSR_TCP_PORT" \
    -v "$SSR_APP_DIR/data:/app/data" \
    "$SSR_IMAGE" >/dev/null
}

show_result() {
  local host_ip

  log "deployment complete"
  host_ip="$(hostname -I 2>/dev/null | cut -d ' ' -f1 || true)"
  if [ -z "$host_ip" ]; then
    host_ip="SERVER_IP"
  fi
  printf "web: http://%s:%s\n" "$host_ip" "$SSR_WEB_PORT"
  printf "admin: http://%s:%s/admin\n" "$host_ip" "$SSR_WEB_PORT"
  printf "tcp: %s\n" "$SSR_TCP_PORT"
  docker ps --format "{{.Names}} {{.Image}} {{.Ports}}" | grep -F "$SSR_CONTAINER" || true
}

need_root
ensure_git
ensure_docker
sync_repo
sync_settings
build_image
run_container
show_result
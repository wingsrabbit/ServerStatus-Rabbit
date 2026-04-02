#!/usr/bin/env bash
set -euo pipefail

SSR_BRANCH=${SSR_BRANCH:-ServerStatus-Rabbit-NG}
SSR_REPO_URL=${SSR_REPO_URL:-https://github.com/wingsrabbit/ServerStatus-Rabbit.git}
SSR_APP_DIR=${SSR_APP_DIR:-}
SSR_IMAGE=${SSR_IMAGE:-serverstatus-rabbit:v0.131}
SSR_SERVER=${SSR_SERVER:-}
SSR_PORT=${SSR_PORT:-9192}
SSR_USER=${SSR_USER:-}
SSR_PASS=${SSR_PASS:-}
SSR_CONTAINER=${SSR_CONTAINER:-}
SSR_SERVICE=${SSR_SERVICE:-}
SSR_RUNTIME_MODE=docker

log() {
  printf '[install-client] %s\n' "$*"
}

fail() {
  printf '[install-client] %s\n' "$*" >&2
  exit 1
}

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    fail 'please run this installer as root'
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
  fail 'unsupported package manager, install required dependencies manually'
}

ensure_required_args() {
  [ -n "$SSR_SERVER" ] || fail 'SSR_SERVER is required'
  [ -n "$SSR_USER" ] || fail 'SSR_USER is required'
  [ -n "$SSR_PASS" ] || fail 'SSR_PASS is required'
}

set_default_app_dir() {
  local safe_user

  if [ -n "$SSR_APP_DIR" ]; then
    return
  fi

  safe_user=$(printf '%s' "$SSR_USER" | tr -cs 'a-zA-Z0-9_.-' '-')
  SSR_APP_DIR="/opt/ServerStatus-Rabbit-$safe_user"
}

ensure_git() {
  if ! command -v git >/dev/null 2>&1; then
    log 'git not found, installing git'
    install_pkg git
  fi
}

ensure_python_runtime() {
  if ! command -v python3 >/dev/null 2>&1; then
    log 'python3 not found, installing python3 and python3-venv'
    install_pkg python3 python3-venv
    return
  fi

  if ! python3 -m venv --help >/dev/null 2>&1; then
    log 'python3 venv support not found, installing python3-venv'
    install_pkg python3-venv
  fi
}

ensure_docker() {
  if ! command -v curl >/dev/null 2>&1; then
    log 'curl not found, installing curl'
    install_pkg curl
  fi

  if ! command -v docker >/dev/null 2>&1; then
    log 'docker not found, installing docker'
    if command -v apt-get >/dev/null 2>&1; then
      if ! install_pkg docker.io; then
        log 'package install failed, falling back to get.docker.com'
        curl -fsSL https://get.docker.com | sh
      fi
    elif command -v dnf >/dev/null 2>&1; then
      if ! dnf install -y docker; then
        log 'package install failed, falling back to get.docker.com'
        curl -fsSL https://get.docker.com | sh
      fi
    elif command -v yum >/dev/null 2>&1; then
      if ! yum install -y docker; then
        log 'package install failed, falling back to get.docker.com'
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
    fail 'docker daemon is not available after installation'
  fi
}

sync_repo() {
  local current_origin dirty_output

  if [ -d "$SSR_APP_DIR/.git" ]; then
    log "updating existing repo in $SSR_APP_DIR"
    if git -C "$SSR_APP_DIR" remote get-url origin >/dev/null 2>&1; then
      current_origin=$(git -C "$SSR_APP_DIR" remote get-url origin || true)
      if [ "$current_origin" != "$SSR_REPO_URL" ]; then
        log "rewriting origin from $current_origin to $SSR_REPO_URL"
        git -C "$SSR_APP_DIR" remote set-url origin "$SSR_REPO_URL"
      fi
    else
      git -C "$SSR_APP_DIR" remote add origin "$SSR_REPO_URL"
    fi

    dirty_output=$(git -C "$SSR_APP_DIR" status --porcelain --untracked-files=all || true)
    if [ -n "$dirty_output" ]; then
      log "repo is dirty, replacing it with a fresh clone"
      rm -rf "$SSR_APP_DIR"
      git clone -b "$SSR_BRANCH" "$SSR_REPO_URL" "$SSR_APP_DIR"
      return
    fi

    git -C "$SSR_APP_DIR" fetch origin "$SSR_BRANCH:refs/remotes/origin/$SSR_BRANCH"
    git -C "$SSR_APP_DIR" checkout -f -B "$SSR_BRANCH" "origin/$SSR_BRANCH"
    git -C "$SSR_APP_DIR" pull --ff-only origin "$SSR_BRANCH"
    return
  fi

  log "cloning $SSR_REPO_URL#$SSR_BRANCH into $SSR_APP_DIR"
  rm -rf "$SSR_APP_DIR"
  git clone -b "$SSR_BRANCH" "$SSR_REPO_URL" "$SSR_APP_DIR"
}

build_image() {
  log "building image $SSR_IMAGE"
  if docker build -t "$SSR_IMAGE" "$SSR_APP_DIR"; then
    SSR_RUNTIME_MODE=docker
    return
  fi

  log 'docker build failed, falling back to python venv mode'
  SSR_RUNTIME_MODE=python
  ensure_python_runtime
  python3 -m venv "$SSR_APP_DIR/venv"
  "$SSR_APP_DIR/venv/bin/pip" install -r "$SSR_APP_DIR/requirements.txt"
}

sanitize_runtime_names() {
  local safe_user

  safe_user=$(printf '%s' "$SSR_USER" | tr -cs 'a-zA-Z0-9_.-' '-')

  if [ -z "$SSR_CONTAINER" ]; then
    SSR_CONTAINER="ssr-client-$safe_user"
  fi
  SSR_CONTAINER=$(printf '%s' "$SSR_CONTAINER" | tr -cs 'a-zA-Z0-9_.-' '-')

  if [ -z "$SSR_SERVICE" ]; then
    SSR_SERVICE="serverstatus-rabbit-client-$safe_user.service"
  fi
}

run_container() {
  log "starting container $SSR_CONTAINER"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl disable --now "$SSR_SERVICE" >/dev/null 2>&1 || true
  fi
  docker rm -f "$SSR_CONTAINER" >/dev/null 2>&1 || true
  docker run -d --restart=always \
    --name "$SSR_CONTAINER" \
    --pid=host \
    --net=host \
    -v /proc:/host/proc:ro \
    -v /sys:/host/sys:ro \
    -v /:/host/rootfs:ro \
    "$SSR_IMAGE" client \
    --server="$SSR_SERVER" \
    --port="$SSR_PORT" \
    --user="$SSR_USER" \
    --pass="$SSR_PASS" >/dev/null
}

run_python_service() {
  local service_path log_path

  log "starting python client service $SSR_SERVICE"
  docker rm -f "$SSR_CONTAINER" >/dev/null 2>&1 || true

  if command -v systemctl >/dev/null 2>&1; then
    service_path="/etc/systemd/system/$SSR_SERVICE"
    cat > "$service_path" <<EOF
[Unit]
Description=ServerStatus-Rabbit Client ($SSR_USER)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$SSR_APP_DIR
ExecStart=$SSR_APP_DIR/venv/bin/python $SSR_APP_DIR/app.py client --server=$SSR_SERVER --port=$SSR_PORT --user=$SSR_USER --pass=$SSR_PASS
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now "$SSR_SERVICE"
    return
  fi

  log_path="/var/log/${SSR_SERVICE%.service}.log"
  pkill -f "$SSR_APP_DIR/app.py client --server=$SSR_SERVER --port=$SSR_PORT --user=$SSR_USER" >/dev/null 2>&1 || true
  nohup "$SSR_APP_DIR/venv/bin/python" "$SSR_APP_DIR/app.py" client --server="$SSR_SERVER" --port="$SSR_PORT" --user="$SSR_USER" --pass="$SSR_PASS" > "$log_path" 2>&1 &
}

show_result() {
  log 'deployment complete'
  printf 'server: %s:%s\n' "$SSR_SERVER" "$SSR_PORT"
  printf 'mode: %s\n' "$SSR_RUNTIME_MODE"
  if [ "$SSR_RUNTIME_MODE" = docker ]; then
    printf 'container: %s\n' "$SSR_CONTAINER"
    docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | grep -F "$SSR_CONTAINER" || true
    return
  fi

  printf 'service: %s\n' "$SSR_SERVICE"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl is-active "$SSR_SERVICE" || true
  fi
}

need_root
ensure_required_args
set_default_app_dir
ensure_git
ensure_docker
sync_repo
build_image
sanitize_runtime_names
if [ "$SSR_RUNTIME_MODE" = docker ]; then
  run_container
else
  run_python_service
fi
show_result
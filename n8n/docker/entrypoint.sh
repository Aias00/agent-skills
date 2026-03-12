#!/bin/sh
set -eu

WORKSPACE="${HOTSPOT_WORKSPACE:-/workspace/agent-skills}"
RUNTIME_ROOT="${HOTSPOT_RUNTIME_ROOT:-/workspace/runtime}"

mkdir -p "$RUNTIME_ROOT" \
  "$RUNTIME_ROOT/wechat-browser-profile" \
  "$RUNTIME_ROOT/xhs-profiles"

if [ -f "$WORKSPACE/wechat-publisher/package.json" ] && [ ! -d "$WORKSPACE/wechat-publisher/node_modules/front-matter" ]; then
  echo "[n8n-entrypoint] Installing wechat-publisher runtime deps..."
  cd "$WORKSPACE/wechat-publisher"
  bun install
fi

if [ -f "$WORKSPACE/post-to-xhs/scripts/package.json" ] && [ ! -d "$WORKSPACE/post-to-xhs/scripts/node_modules/playwright" ]; then
  echo "[n8n-entrypoint] Installing post-to-xhs runtime deps..."
  cd "$WORKSPACE/post-to-xhs/scripts"
  npm ci
fi

cd "$WORKSPACE"
exec /docker-entrypoint.sh "$@"

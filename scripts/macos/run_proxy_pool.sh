#!/usr/bin/env bash
# Start the optional local SOCKS5 proxy pool using the macOS virtualenv.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "此脚本只用于 macOS；当前系统：$(uname -s)" >&2
  exit 2
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "未找到虚拟环境，请先运行 scripts/macos/bootstrap.sh" >&2
  exit 1
fi

cd "$REPO_ROOT"
exec "$PYTHON" "$REPO_ROOT/start_proxy_pool.py" "$@"

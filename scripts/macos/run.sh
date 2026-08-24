#!/usr/bin/env bash
# Run the macOS-compatible Python CLI with the repository virtualenv.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "此脚本只用于 macOS；当前系统：$(uname -s)" >&2
  exit 2
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "未找到虚拟环境：$PYTHON" >&2
  echo "请先运行：$REPO_ROOT/scripts/macos/bootstrap.sh" >&2
  exit 1
fi

if [[ ! -f "$REPO_ROOT/config.json" ]]; then
  echo "未找到 config.json。请先运行 bootstrap.sh 并填写配置。" >&2
  exit 1
fi

cd "$REPO_ROOT"
exec "$PYTHON" "$REPO_ROOT/chatgpt_phone_reg.py" "$@"

#!/usr/bin/env bash
# Launch the native macOS registration workbench.
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

if ! "$PYTHON" -c 'import PySide6' >/dev/null 2>&1; then
  echo "未安装 macOS GUI 依赖。正在安装 requirements-macos-gui.txt…"
  "$PYTHON" -m pip install -r "$REPO_ROOT/requirements-macos-gui.txt"
fi

cd "$REPO_ROOT"
exec "$PYTHON" "$REPO_ROOT/scripts/macos/gui_app.py" "$@"

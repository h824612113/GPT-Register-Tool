#!/usr/bin/env bash
# Bootstrap a macOS checkout for the cross-platform Python backend.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"
VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-${TMPDIR:-/tmp}/gpt-register-tool-pip-cache}"
PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS="${PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS:-180}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "此脚本只用于 macOS；当前系统：$(uname -s)" >&2
  exit 2
fi

if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$PYTHON_BIN" ]] || ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "找不到 $PYTHON_BIN。请先安装 Python 3.10+（推荐：brew install python@3.12）。" >&2
  exit 1
fi

HOST_ARCH="$(uname -m)"
PYTHON_ARCH="$("$PYTHON_BIN" -c 'import platform; print(platform.machine())' 2>/dev/null || true)"
if [[ "$HOST_ARCH" == "arm64" && "$PYTHON_ARCH" != "arm64" ]]; then
  for candidate in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3; do
    if [[ -x "$candidate" ]] && [[ "$("$candidate" -c 'import platform; print(platform.machine())' 2>/dev/null || true)" == "arm64" ]]; then
      echo "检测到 $PYTHON_BIN ($PYTHON_ARCH)，切换到原生 Apple Silicon Python：$candidate"
      PYTHON_BIN="$candidate"
      PYTHON_ARCH="arm64"
      break
    fi
  done
fi
if [[ "$HOST_ARCH" == "arm64" && "$PYTHON_ARCH" != "arm64" ]]; then
  echo "当前 Python ($PYTHON_BIN) 不是 Apple Silicon 原生版本。请安装原生 Python：brew install python@3.12" >&2
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "$PYTHON_BIN 版本低于 Python 3.10，请升级后重试。" >&2
  exit 1
fi

if [[ ! -f "$REPO_ROOT/config.json" ]]; then
  cp "$REPO_ROOT/config.example.json" "$REPO_ROOT/config.json"
  echo "已从 config.example.json 创建 config.json，请先填写邮箱、代理和支付配置。"
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  VENV_ARCH="$("$VENV_DIR/bin/python" -c 'import platform; print(platform.machine())' 2>/dev/null || true)"
  if [[ "$HOST_ARCH" == "arm64" && "$VENV_ARCH" != "arm64" ]]; then
    echo "现有虚拟环境是 $VENV_ARCH，重建为 Apple Silicon 原生环境：$VENV_DIR"
    "$PYTHON_BIN" -m venv --clear "$VENV_DIR"
  fi
fi
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "创建虚拟环境：$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"
if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "修复虚拟环境中的 pip"
  "$PYTHON" -m ensurepip --upgrade
fi
echo "升级 pip 并安装 Python 依赖"
mkdir -p "$PIP_CACHE_DIR"
PIP_CACHE_DIR="$PIP_CACHE_DIR" "$PYTHON" -m pip install --upgrade pip
PIP_CACHE_DIR="$PIP_CACHE_DIR" "$PYTHON" -m pip install -r "$REPO_ROOT/requirements.txt"
if [[ "${INSTALL_GUI:-1}" == "1" ]]; then
  echo "安装 macOS 图形界面依赖"
  PIP_CACHE_DIR="$PIP_CACHE_DIR" "$PYTHON" -m pip install -r "$REPO_ROOT/requirements-macos-gui.txt"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "警告：未找到 Node.js 18+。Sentinel 提取需要 Node.js（可执行 brew install node@22）。" >&2
fi

echo "安装 Playwright Chromium"
PIP_CACHE_DIR="$PIP_CACHE_DIR" PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS="$PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS" "$PYTHON" - <<'PY'
import os
import subprocess
import sys

timeout = int(os.environ["PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS"])
try:
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        timeout=timeout,
    )
except subprocess.TimeoutExpired:
    print(
        f"Playwright Chromium 下载超过 {timeout} 秒；请检查网络后重试，"
        "或手动执行 .venv/bin/python -m playwright install chromium。",
        file=sys.stderr,
    )
    raise SystemExit(124)
PY

echo "运行环境预检"
"$PYTHON" "$REPO_ROOT/scripts/preflight_env.py"
echo
echo "完成。图形界面：$REPO_ROOT/scripts/macos/run_gui.sh"
echo "命令行帮助：$REPO_ROOT/scripts/macos/run.sh --help"

#!/usr/bin/env python3
"""环境预检：确认 Node.js、Playwright Chromium 和关键 Python 包就绪。

这些是 README「环境要求」里 `pip install -r requirements.txt` 覆盖不到的运行期
前置依赖：Sentinel Token 的 quickjs 提取器需要 `node`，协议支付的 Stripe init
需要 Playwright Chromium。缺失时运行期表现为 OTP 静默丢失或支付链接超时，很难排查，
因此在首次启动前用本脚本一次性检出。

退出码：0 表示全部通过；非 0 表示存在缺失项（数量即失败项数）。
"""

from __future__ import annotations

import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def check_python_version() -> tuple[bool, str, str]:
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        return True, f"Python {major}.{minor}", ""
    return False, f"Python {major}.{minor}", "安装 Python 3.10+（https://www.python.org/downloads/）"


def _python_command(*args: str) -> str:
    """Return a copy/pasteable command using the interpreter running this check."""
    command = [sys.executable, *args]
    return shlex.join(command)


def check_platform() -> tuple[bool, str, str]:
    system = platform.system()
    machine = platform.machine() or "unknown"
    if system in {"Windows", "Darwin", "Linux"}:
        return True, f"{system} ({machine})", ""
    return False, f"{system or 'unknown'} ({machine})", "仅支持 Windows、macOS 和 Linux"


def check_node() -> tuple[bool, str, str]:
    exe = shutil.which("node")
    if not exe:
        return False, "node 不在 PATH", "安装 Node.js 18+（https://nodejs.org）并确保 node 在 PATH"
    try:
        proc = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=10
        )
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"无法执行 node：{exc}", "重新安装 Node.js 18+"
    version = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0:
        return False, version or "node 执行失败", "重新安装 Node.js 18+"
    try:
        major = int(version.lstrip("v").split(".", 1)[0])
    except (TypeError, ValueError):
        major = 0
    if major < 18:
        return False, version or "node (版本未知)", "升级到 Node.js 18+"
    return True, version or "node (版本未知)", ""


def check_import(module: str, pip_name: str) -> tuple[bool, str, str]:
    try:
        __import__(module)
    except Exception as exc:
        return False, f"{module} 不可导入：{exc}", f"{_python_command('-m', 'pip', 'install', pip_name)}"
    return True, module, ""


def check_playwright_chromium() -> tuple[bool, str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return False, f"playwright 未安装：{exc}", f"{_python_command('-m', 'pip', 'install', 'playwright')}"
    try:
        with sync_playwright() as p:
            path = p.chromium.executable_path
    except Exception as exc:
        return False, f"无法查询 chromium：{exc}", f"{_python_command('-m', 'playwright', 'install', 'chromium')}"
    if path and Path(path).exists():
        return True, "chromium 已安装", ""
    return False, "chromium 未下载", f"{_python_command('-m', 'playwright', 'install', 'chromium')}"


CHECKS = (
    ("运行平台", check_platform, True),
    ("Python 版本", check_python_version, True),
    ("Node.js (Sentinel quickjs)", check_node, True),
    ("Playwright Chromium (Stripe init)", check_playwright_chromium, True),
    ("curl_cffi (协议支付 TLS)", lambda: check_import("curl_cffi", "curl_cffi"), True),
    ("requests", lambda: check_import("requests", "requests"), True),
    ("PyNaCl (Agent Identity Ed25519)", lambda: check_import("nacl", "PyNaCl"), False),
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("GPT-Register-Tool 环境预检\n" + "=" * 40)
    failures: list[tuple[str, str, str]] = []
    for label, check, required in CHECKS:
        ok, detail, fix = check()
        tag = "  OK  " if ok else ("FAIL " if required else "WARN ")
        print(f"[{tag}] {label}: {detail}")
        if not ok and required:
            failures.append((label, detail, fix))

    print("=" * 40)
    if not failures:
        print("全部关键依赖就绪。")
        return 0

    print(f"发现 {len(failures)} 项缺失，修复方式：")
    for label, _detail, fix in failures:
        print(f"  - {label}: {fix or '见文档'}")
    return len(failures)


if __name__ == "__main__":
    raise SystemExit(main())

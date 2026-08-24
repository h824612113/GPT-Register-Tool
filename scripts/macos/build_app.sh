#!/usr/bin/env bash
# Create a double-clickable .app wrapper for the repository-local GUI.
#
# LaunchServices refuses script-based executables (kLSNoExecutableErr), so the
# bundle executable is a tiny compiled Mach-O launcher that execs the repository
# launcher. Requires Xcode Command Line Tools (clang).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
APP_DIR="$REPO_ROOT/dist/GPT Register Tool.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
LAUNCH_SCRIPT="$REPO_ROOT/scripts/macos/run_gui.sh"
ICON_SOURCE="$REPO_ROOT/services/mail-otp-web/static/black-kitten.png"

if [[ ! -f "$LAUNCH_SCRIPT" ]]; then
  echo "缺少 $LAUNCH_SCRIPT，请先同步仓库。" >&2
  exit 1
fi

if ! command -v clang >/dev/null 2>&1; then
  echo "未找到 clang。请先安装 Xcode Command Line Tools：xcode-select --install" >&2
  exit 1
fi

if [[ -e "$APP_DIR" ]]; then
  rm -rf -- "$APP_DIR"
fi
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

TMP_C="${TMPDIR:-/tmp}/gpt_register_launcher_$$.c"
trap 'rm -f "$TMP_C"' EXIT
cat > "$TMP_C" <<EOF
#include <stdio.h>
#include <unistd.h>

int main(void) {
    char *const argv[] = {"$LAUNCH_SCRIPT", NULL};
    execv(argv[0], argv);
    perror("launch failed");
    return 127;
}
EOF

if ! clang -O2 -o "$MACOS_DIR/GPTRegisterTool" "$TMP_C"; then
  echo "clang 编译 launcher 失败。" >&2
  exit 1
fi

cat > "$CONTENTS_DIR/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDisplayName</key>
  <string>GPT Register Tool</string>
  <key>CFBundleExecutable</key>
  <string>GPTRegisterTool</string>
  <key>CFBundleIdentifier</key>
  <string>local.gptregistertool.macos</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>GPT Register Tool</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF

if [[ -f "$ICON_SOURCE" ]]; then
  cp "$ICON_SOURCE" "$RESOURCES_DIR/black-kitten.png"
fi

echo "已生成：$APP_DIR"
echo "启动：open \"$APP_DIR\""

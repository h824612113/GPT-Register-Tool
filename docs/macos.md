# macOS 运行说明

macOS 通过原生 PySide6 注册工作台运行仓库的 Python 业务核心，不运行 `SmsWorkbench` WPF 桌面端。WPF 依赖 Windows Desktop，因此不能通过 .NET SDK 在 macOS 上直接编译。

## 快速开始

在仓库根目录执行：

```bash
chmod +x scripts/macos/*.sh
./scripts/macos/bootstrap.sh
```

首次运行会：

1. 检查 macOS 和 Python 3.10+。
2. 创建 `.venv` 虚拟环境。
3. 安装 `requirements.txt`。
4. 安装 Playwright Chromium。
5. 在缺少时创建 `config.json`。
6. 执行 `scripts/preflight_env.py` 预检。

Node.js 18+ 是 Sentinel quickjs 的运行时依赖。推荐使用 Homebrew 安装：

```bash
brew install node@22
```

## 启动图形界面

```bash
./scripts/macos/run_gui.sh
```

界面支持 Chatai/邮箱池、ReMail 长效邮箱、CFWorker、SMSBower 手机号和单邮箱凭据五种注册入口，可设置数量、并发、代理、AT-only 与手机验证策略，并实时显示后端日志。注册逻辑仍由 `chatgpt_phone_reg.py` 执行。

生成可双击启动的本地 `.app` 包装：

```bash
./scripts/macos/build_app.sh
open "dist/GPT Register Tool.app"
```

构建 `.app` 需要 Xcode Command Line Tools（`clang`）；未安装时脚本会提示运行
`xcode-select --install`。

这个 `.app` 使用仓库内的 `.venv` 和源码，因此移动仓库后需要重新执行 `build_app.sh`。

## 命令行启动

所有参数原样传给 `chatgpt_phone_reg.py`：

```bash
./scripts/macos/run.sh --help
./scripts/macos/run.sh --chatai-mailbox-file hotmail.txt --count 1 --workers 1
```

可选的本地代理池：

```bash
./scripts/macos/run_proxy_pool.sh --port 18080 --stats-port 18081
```

脚本默认使用 `.venv/bin/python`，也可以通过 `PYTHON_BIN` 指定解释器：

```bash
PYTHON_BIN=/opt/homebrew/bin/python3 ./scripts/macos/run.sh --help
```

## macOS 与 Windows 的边界

- Python 模块、配置文件、Session、SQLite、邮箱和支付协议逻辑共用。
- macOS 图形界面位于 `scripts/macos/gui_app.py`，通过 `QProcess` 调用同一 Python 后端。
- `SmsWorkbench/` 的 WPF 界面、`scripts/build_installer.ps1` 和 Windows 安装器只在 Windows 上使用。
- macOS 不需要 .NET SDK；不要运行 `SmsWorkbench/build_dotnet.ps1`。
- 运行数据仍写入仓库下的 `runtime/`、`sessions/`，这些路径已被 Git 忽略。

#!/usr/bin/env python3
"""Native macOS registration workbench backed by the existing Python CLI."""

from __future__ import annotations

import json
import os
import shlex
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QTabWidget,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sms_tool.macos_gui_command import (  # noqa: E402
    RegistrationGuiOptions,
    build_registration_args,
    validate_options,
)


SOURCE_INDEX = {"pool": 0, "remail": 1, "cfworker": 2, "phone": 3, "explicit": 4}
SECRET_FLAGS = {
    "--password",
    "--email-password",
    "--email-refresh-token",
    "--email-access-token",
    "--remail-token",
}


def _redacted_command(program: str, args: list[str]) -> str:
    rendered = [program]
    hide_next = False
    for value in args:
        if hide_next:
            rendered.append("••••••••")
            hide_next = False
            continue
        rendered.append(value)
        hide_next = value in SECRET_FLAGS
    return shlex.join(rendered)


class RegistrationWindow(QMainWindow):
    def __init__(self, repo_root: Path | str = REPO_ROOT):
        super().__init__()
        self.repo_root = Path(repo_root).resolve()
        self.python_path = self.repo_root / ".venv" / "bin" / "python"
        self.backend_path = self.repo_root / "chatgpt_phone_reg.py"
        self.config_path = self.repo_root / "config.json"
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_process_output)
        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_process_error)

        self.setWindowTitle("GPT Register Tool · macOS")
        self.setMinimumSize(1080, 720)
        self.resize(1260, 820)
        icon = self.repo_root / "services" / "mail-otp-web" / "static" / "black-kitten.png"
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))

        self._build_ui()
        self._load_config_defaults()
        self._connect_preview_signals()
        self._source_changed()
        self._refresh_preview()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 18, 22, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("GPT Register Tool")
        title.setObjectName("title")
        subtitle = QLabel("macOS 注册工作台 · 复用 Python 注册核心")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        self.config_status = QLabel("正在检查配置…")
        self.config_status.setObjectName("statusPill")
        header.addWidget(self.config_status)
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)
        outer.addLayout(header)

        content = QGridLayout()
        content.setHorizontalSpacing(16)
        content.setVerticalSpacing(0)
        content.setColumnStretch(0, 0)
        content.setColumnStretch(1, 1)
        outer.addLayout(content, 1)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_card.setFixedWidth(430)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(12)

        section_title = QLabel("注册参数")
        section_title.setObjectName("sectionTitle")
        form_layout.addWidget(section_title)

        common_form = QFormLayout()
        common_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        common_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        common_form.setHorizontalSpacing(12)
        common_form.setVerticalSpacing(10)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Chatai / 邮箱池", "pool")
        self.source_combo.addItem("ReMail 长效邮箱", "remail")
        self.source_combo.addItem("CFWorker 邮箱", "cfworker")
        self.source_combo.addItem("手机号注册 (SMSBower)", "phone")
        self.source_combo.addItem("单邮箱凭据", "explicit")
        common_form.addRow("注册方式", self.source_combo)

        numbers = QHBoxLayout()
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 200)
        self.count_spin.setValue(1)
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 20)
        self.workers_spin.setValue(1)
        numbers.addWidget(QLabel("数量"))
        numbers.addWidget(self.count_spin)
        numbers.addSpacing(10)
        numbers.addWidget(QLabel("并发"))
        numbers.addWidget(self.workers_spin)
        common_form.addRow("批次", numbers)
        form_layout.addLayout(common_form)

        self.source_stack = QStackedWidget()
        self.source_stack.addWidget(self._pool_page())
        self.source_stack.addWidget(self._remail_page())
        self.source_stack.addWidget(self._cfworker_page())
        self.source_stack.addWidget(self._phone_page())
        self.source_stack.addWidget(self._explicit_page())
        form_layout.addWidget(self.source_stack)

        advanced_title = QLabel("通用选项")
        advanced_title.setObjectName("sectionTitle")
        form_layout.addWidget(advanced_title)
        advanced = QFormLayout()
        advanced.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        advanced.setHorizontalSpacing(12)
        advanced.setVerticalSpacing(10)
        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText("http://127.0.0.1:7897")
        advanced.addRow("注册代理", self.proxy_edit)
        self.proxy_pool_edit = QPlainTextEdit()
        self.proxy_pool_edit.setPlaceholderText("每行一个，或逗号分隔")
        self.proxy_pool_edit.setMaximumHeight(60)
        self.proxy_pool_edit.textChanged.connect(self._on_proxy_pool_changed)
        advanced.addRow("代理池", self.proxy_pool_edit)
        self.account_password_edit = QLineEdit()
        self.account_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.account_password_edit.setPlaceholderText("留空则自动生成")
        advanced.addRow("账号密码", self.account_password_edit)
        self.registration_mode_combo = QComboBox()
        self.registration_mode_combo.addItem("配置默认", "")
        self.registration_mode_combo.addItem("Passwordless", "passwordless")
        self.registration_mode_combo.addItem("Password", "password")
        self.registration_mode_combo.addItem("HAR", "har")
        self.registration_mode_combo.addItem("Legacy", "legacy")
        advanced.addRow("认证模式", self.registration_mode_combo)
        form_layout.addLayout(advanced)

        toggles = QHBoxLayout()
        self.at_only_check = QCheckBox("仅注册并保存 AT")
        self.at_only_check.setChecked(True)
        self.disable_phone_check = QCheckBox("不做手机验证")
        self.disable_phone_check.setChecked(True)
        toggles.addWidget(self.at_only_check)
        toggles.addWidget(self.disable_phone_check)
        form_layout.addLayout(toggles)

        self.validation_label = QLabel("")
        self.validation_label.setObjectName("validation")
        self.validation_label.setWordWrap(True)
        form_layout.addWidget(self.validation_label)

        actions = QHBoxLayout()
        self.start_button = QPushButton("开始注册")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_registration)
        self.stop_button.clicked.connect(self.stop_registration)
        actions.addWidget(self.start_button, 1)
        actions.addWidget(self.stop_button)
        form_layout.addLayout(actions)
        content.addWidget(form_card, 0, 0)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(18, 18, 18, 18)
        log_layout.setSpacing(10)
        log_header = QHBoxLayout()
        log_title = QLabel("运行日志")
        log_title.setObjectName("sectionTitle")
        self.run_status = QLabel("待机")
        self.run_status.setObjectName("statusPill")
        clear_button = QPushButton("清空")
        clear_button.clicked.connect(lambda: self.log_output.clear())
        sessions_button = QPushButton("打开 Sessions")
        sessions_button.clicked.connect(self._open_sessions)
        log_header.addWidget(log_title)
        log_header.addStretch(1)
        log_header.addWidget(self.run_status)
        log_header.addWidget(sessions_button)
        log_header.addWidget(clear_button)
        log_layout.addLayout(log_header)

        preview_label = QLabel("命令预览（敏感参数已隐藏）")
        preview_label.setObjectName("fieldHint")
        log_layout.addWidget(preview_label)
        self.command_preview_edit = QLineEdit()
        self.command_preview_edit.setReadOnly(True)
        self.command_preview_edit.setObjectName("commandPreview")
        log_layout.addWidget(self.command_preview_edit)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        mono = QFont("SF Mono")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(11)
        self.log_output.setFont(mono)
        self.log_output.setPlaceholderText("点击“开始注册”后，这里会显示完整后端输出。")
        log_layout.addWidget(self.log_output, 1)
        content.addWidget(log_card, 0, 1)

        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f3f1ec; color: #25292e; font-size: 13px; }
            #title { font-size: 25px; font-weight: 750; }
            #subtitle, #fieldHint { color: #747b83; }
            #card { background: #fbfaf7; border: 1px solid #ded9d0; border-radius: 14px; }
            #sectionTitle { font-size: 15px; font-weight: 700; }
            #statusPill { background: #e9e5dc; border-radius: 10px; padding: 5px 10px; color: #5d646b; }
            #validation { color: #b42318; min-height: 18px; }
            QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
                background: #ffffff; border: 1px solid #d6d1c8; border-radius: 7px; padding: 7px;
                selection-background-color: #315efb;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus { border-color: #315efb; }
            QPushButton { background: #ffffff; border: 1px solid #d6d1c8; border-radius: 8px; padding: 8px 14px; }
            QPushButton:hover { background: #f0ede7; }
            QPushButton:disabled { color: #a5a5a5; background: #efefef; }
            #primaryButton { background: #20242a; color: white; border-color: #20242a; font-weight: 700; }
            #primaryButton:hover { background: #343a42; }
            #commandPreview { background: #eeece7; color: #4b5259; }
            """
        )

    def _pool_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.mailbox_text_edit = QPlainTextEdit()
        self.mailbox_text_edit.setPlaceholderText(
            "直接粘贴邮箱行，每行一个；支持 iCloud 接码链接（email----接码URL）"
        )
        self.mailbox_text_edit.setMinimumHeight(130)
        layout.addRow("邮箱池", self.mailbox_text_edit)
        row = QHBoxLayout()
        browse = QPushButton("从 txt 载入…")
        browse.clicked.connect(self._choose_mailbox_file)
        row.addWidget(browse)
        row.addStretch(1)
        layout.addRow("", row)
        hint = QLabel("支持 Chatai、iCloud 接码链接、ReMail、CFWorker、Gmail 等混合格式，每行一个。")
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addRow("", hint)
        return page

    def _remail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        hint = QLabel("使用 config.json 中的 ReMail API Key 购买长效邮箱，并补足稳定 HTTP 200 AT 数量。")
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return page

    def _cfworker_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.cfworker_domain_edit = QLineEdit()
        self.cfworker_domain_edit.setPlaceholderText("mail.example.com")
        layout.addRow("邮箱域名", self.cfworker_domain_edit)
        return page

    def _phone_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.smsbower_country_edit = QLineEdit()
        self.smsbower_country_edit.setPlaceholderText("留空使用 config.json")
        layout.addRow("国家 ID", self.smsbower_country_edit)
        return page

    def _explicit_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("user@example.com")
        self.email_password_edit = QLineEdit()
        self.email_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_refresh_token_edit = QLineEdit()
        self.email_refresh_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_access_token_edit = QLineEdit()
        self.email_access_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.remail_token_edit = QLineEdit()
        self.remail_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("邮箱", self.email_edit)
        layout.addRow("邮箱密码", self.email_password_edit)
        layout.addRow("Refresh Token", self.email_refresh_token_edit)
        layout.addRow("Access Token", self.email_access_token_edit)
        layout.addRow("ReMail Token", self.remail_token_edit)
        return page

    def _connect_preview_signals(self) -> None:
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        self.count_spin.valueChanged.connect(self._refresh_preview)
        self.workers_spin.valueChanged.connect(self._refresh_preview)
        self.registration_mode_combo.currentIndexChanged.connect(self._refresh_preview)
        self.at_only_check.toggled.connect(self._refresh_preview)
        self.disable_phone_check.toggled.connect(self._refresh_preview)
        for edit in (
            self.mailbox_text_edit,
            self.cfworker_domain_edit,
            self.smsbower_country_edit,
            self.email_edit,
            self.email_password_edit,
            self.email_refresh_token_edit,
            self.email_access_token_edit,
            self.remail_token_edit,
            self.proxy_edit,
            self.proxy_pool_edit,
            self.account_password_edit,
        ):
            edit.textChanged.connect(self._refresh_preview)

    def _load_config_defaults(self) -> None:
        if not self.config_path.is_file():
            self.config_status.setText("缺少 config.json")
            return
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            self.config_status.setText("config.json 无效")
            self.validation_label.setText(str(exc))
            return
        email_cfg = config.get("email_registration") if isinstance(config.get("email_registration"), dict) else {}
        proxy_cfg = config.get("proxy") if isinstance(config.get("proxy"), dict) else {}
        token_file = str(email_cfg.get("token_file") or "").strip()
        if token_file:
            path = Path(token_file).expanduser()
            if not path.is_absolute():
                path = self.repo_root / path
            if path.is_file():
                try:
                    self.mailbox_text_edit.setPlainText(path.read_text(encoding="utf-8-sig"))
                except OSError:
                    pass
        self.cfworker_domain_edit.setText(str(email_cfg.get("cfworker_domain") or ""))
        self.proxy_edit.setText(str(proxy_cfg.get("registration") or proxy_cfg.get("default") or ""))
        pool = proxy_cfg.get("pool") or []
        if isinstance(pool, list):
            self.proxy_pool_edit.setPlainText(", ".join(str(value) for value in pool if str(value).strip()))
        elif isinstance(pool, str):
            self.proxy_pool_edit.setPlainText(pool)
        self.config_status.setText("config.json 已加载")

    def _choose_mailbox_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择邮箱池文件",
            str(self.repo_root),
            "文本文件 (*.txt);;所有文件 (*)",
        )
        if not selected:
            return
        try:
            text = Path(selected).read_text(encoding="utf-8-sig")
        except OSError as exc:
            QMessageBox.warning(self, "无法读取文件", str(exc))
            return
        self.mailbox_text_edit.setPlainText(text)
        self._refresh_preview()

    def _source_changed(self) -> None:
        source = str(self.source_combo.currentData() or "pool")
        self.source_stack.setCurrentIndex(SOURCE_INDEX[source])
        phone_source = source == "phone"
        self.workers_spin.setEnabled(not phone_source)
        self.disable_phone_check.setEnabled(not phone_source)
        self._refresh_preview()

    def collect_options(self) -> RegistrationGuiOptions:
        return RegistrationGuiOptions(
            source=str(self.source_combo.currentData() or "pool"),
            count=self.count_spin.value(),
            workers=self.workers_spin.value(),
            mailbox_file="",
            mailbox_text=self.mailbox_text_edit.toPlainText(),
            email=self.email_edit.text(),
            email_password=self.email_password_edit.text(),
            email_refresh_token=self.email_refresh_token_edit.text(),
            email_access_token=self.email_access_token_edit.text(),
            remail_token=self.remail_token_edit.text(),
            cfworker_domain=self.cfworker_domain_edit.text(),
            smsbower_country=self.smsbower_country_edit.text(),
            proxy=self.proxy_edit.text(),
            proxy_pool=self.proxy_pool_edit.toPlainText(),
            account_password=self.account_password_edit.text(),
            registration_mode=str(self.registration_mode_combo.currentData() or ""),
            registration_at_only=self.at_only_check.isChecked(),
            disable_phone_verification=self.disable_phone_check.isChecked(),
        )

    def _write_mailbox_text(self, text: str) -> Path:
        runtime_dir = self.repo_root / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        target = runtime_dir / "macos_gui_mailbox_input.txt"
        target.write_text(text, encoding="utf-8")
        return target

    def _resolved_options(self) -> RegistrationGuiOptions:
        options = self.collect_options()
        if options.source == "pool" and options.mailbox_text.strip():
            path = self._write_mailbox_text(options.mailbox_text)
            options = replace(options, mailbox_file=str(path), mailbox_text="")
        return options

    def command_preview(self) -> str:
        try:
            args = build_registration_args(self._resolved_options())
        except ValueError:
            return ""
        return _redacted_command(str(self.python_path), [str(self.backend_path), *args])

    def _refresh_preview(self) -> None:
        errors = validate_options(self.collect_options())
        self.validation_label.setText(errors[0] if errors else "")
        self.command_preview_edit.setText(self.command_preview())

    def start_registration(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        options = self._resolved_options()
        errors = validate_options(options)
        if not self.config_path.is_file():
            errors.insert(0, "项目根目录缺少 config.json。")
        if not self.python_path.is_file():
            errors.insert(0, "未找到 .venv/bin/python，请先运行 scripts/macos/bootstrap.sh。")
        if not self.backend_path.is_file():
            errors.insert(0, "未找到 chatgpt_phone_reg.py。")
        if errors:
            QMessageBox.warning(self, "无法开始注册", "\n".join(errors))
            return

        args = [str(self.backend_path), *build_registration_args(options)]
        self.log_output.clear()
        self._append_log("$ " + _redacted_command(str(self.python_path), args) + "\n\n")
        self.run_status.setText("正在启动…")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.process.setWorkingDirectory(str(self.repo_root))
        self.process.start(str(self.python_path), args)

    def stop_registration(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self.run_status.setText("正在停止…")
        self.process.terminate()
        QTimer.singleShot(3000, self._kill_if_running)

    def _kill_if_running(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _read_process_output(self) -> None:
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        self._append_log(data)

    def _append_log(self, text: str) -> None:
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.log_output.setTextCursor(cursor)
        self.log_output.ensureCursorVisible()

    def _on_started(self) -> None:
        self.run_status.setText("运行中")

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.run_status.setText("完成" if exit_code == 0 else f"失败 · {exit_code}")
        self._append_log(f"\n[process exited with code {exit_code}]\n")

    def _on_process_error(self, _error: QProcess.ProcessError) -> None:
        self._append_log(f"\n[process error] {self.process.errorString()}\n")

    def _open_sessions(self) -> None:
        directory = self.repo_root / "sessions"
        directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _on_proxy_pool_changed(self) -> None:
        text = self.proxy_pool_edit.toPlainText()
        if "\n" in text or "\r" in text:
            lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
            if lines:
                self.proxy_pool_edit.blockSignals(True)
                self.proxy_pool_edit.setPlainText(", ".join(lines))
                self.proxy_pool_edit.blockSignals(False)

    def _open_settings(self) -> None:
        import sys as _sys
        _sys.path.insert(0, str(self.repo_root / "scripts" / "macos"))
        from gui_settings_dialog import SettingsDialog as _SD
        _sys.path.pop(0)
        dialog = _SD(self.config_path, self)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1000)
        event.accept()


def create_application(argv: list[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    app = QApplication(list(argv or []))
    app.setApplicationName("GPT Register Tool")
    app.setOrganizationName("GPT Register Tool")
    app.setStyle("Fusion")
    return app


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv or os.environ.get("GPT_REGISTER_GUI_SMOKE_TEST") == "1"
    argv = [value for value in sys.argv if value != "--smoke-test"]
    app = create_application(argv)
    window = RegistrationWindow()
    window.show()
    if smoke_test:
        QTimer.singleShot(100, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

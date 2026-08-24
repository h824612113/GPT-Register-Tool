"""Settings dialog for the macOS registration workbench."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _make_hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #747b83; font-size: 12px;")
    lbl.setWordWrap(True)
    return lbl


class SettingsDialog(QDialog):
    """Modal settings dialog for editing config.json sections."""

    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self._config: dict = {}
        self._edits: dict[str, QLineEdit | QPlainTextEdit | QSpinBox | QCheckBox | QComboBox] = {}
        self._combo_edits: dict[str, QComboBox] = {}
        self.setWindowTitle("配置设置")
        self.setMinimumSize(560, 600)
        self.resize(600, 660)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        tabs = QTabWidget()
        tabs.addTab(self._build_proxy_tab(), "代理设置")
        tabs.addTab(self._build_sms_tab(), "接码设置")
        tabs.addTab(self._build_registration_tab(), "注册参数")
        tabs.addTab(self._build_mail_tab(), "邮箱服务")
        tabs.addTab(self._build_other_tab(), "其他")
        layout.addWidget(tabs)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setStyleSheet("""
            QDialog, QWidget { background: #f3f1ec; color: #25292e; font-size: 13px; }
            QTabWidget::pane { background: #fbfaf7; border: 1px solid #ded9d0; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; }
            QTabBar::tab:selected { font-weight: 700; }
            QLineEdit, QSpinBox, QComboBox {
                background: #ffffff; border: 1px solid #d6d1c8; border-radius: 6px; padding: 6px;
                selection-background-color: #315efb;
            }
            QLineEdit:focus { border-color: #315efb; }
            QPushButton { background: #ffffff; border: 1px solid #d6d1c8; border-radius: 8px; padding: 8px 14px; }
            #primaryButton { background: #20242a; color: white; border-color: #20242a; font-weight: 700; }
            #primaryButton:hover { background: #343a42; }
        """)

    def _scroll_wrap(self, widget: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    # ========== Proxy tab ==========
    def _build_proxy_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._edits["proxy.registration"] = QLineEdit()
        self._edits["proxy.registration"].setPlaceholderText("http://127.0.0.1:7897")
        form.addRow("注册代理", self._edits["proxy.registration"])

        self._edits["proxy.default"] = QLineEdit()
        self._edits["proxy.default"].setPlaceholderText("http://127.0.0.1:7897")
        form.addRow("默认代理", self._edits["proxy.default"])

        self._edits["proxy.pool"] = QPlainTextEdit()
        self._edits["proxy.pool"].setPlaceholderText("每行一个，或逗号分隔")
        self._edits["proxy.pool"].setMaximumHeight(80)
        self._edits["proxy.pool"].textChanged.connect(self._on_proxy_pool_changed)
        form.addRow("代理池", self._edits["proxy.pool"])

        self._edits["mailbox_proxy"] = QLineEdit()
        self._edits["mailbox_proxy"].setPlaceholderText("http://127.0.0.1:7897")
        form.addRow("邮箱代理", self._edits["mailbox_proxy"])

        layout.addLayout(form)
        layout.addWidget(_make_hint("代理池中多个地址用逗号分隔，注册时轮询使用。"))
        layout.addStretch(1)
        return self._scroll_wrap(root)

    # ========== SMS tab ==========
    def _build_sms_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        # --- SMSBower ---
        sms_title = QLabel("SMSBower 接码配置")
        sms_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")
        form.addRow("", sms_title)

        self._edits["smsbower.api_key"] = QLineEdit()
        self._edits["smsbower.api_key"].setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key", self._edits["smsbower.api_key"])

        self._edits["smsbower.service"] = QLineEdit()
        self._edits["smsbower.service"].setPlaceholderText("dr")
        form.addRow("服务 ID", self._edits["smsbower.service"])

        self._edits["smsbower.service_name"] = QLineEdit()
        self._edits["smsbower.service_name"].setPlaceholderText("OpenAI (ChatGPT)")
        form.addRow("服务名称", self._edits["smsbower.service_name"])

        self._edits["smsbower.country"] = QLineEdit()
        self._edits["smsbower.country"].setPlaceholderText("38")
        form.addRow("国家 ID", self._edits["smsbower.country"])

        self._edits["smsbower.country_name"] = QLineEdit()
        self._edits["smsbower.country_name"].setPlaceholderText("Ghana")
        form.addRow("国家名称", self._edits["smsbower.country_name"])

        self._edits["smsbower.country_prefix"] = QLineEdit()
        self._edits["smsbower.country_prefix"].setPlaceholderText("+233")
        form.addRow("国家前缀", self._edits["smsbower.country_prefix"])

        price_row = QHBoxLayout()
        self._edits["smsbower.min_price"] = QLineEdit()
        self._edits["smsbower.min_price"].setPlaceholderText("0.054")
        self._edits["smsbower.target_price"] = QLineEdit()
        self._edits["smsbower.target_price"].setPlaceholderText("0.054")
        self._edits["smsbower.max_price"] = QLineEdit()
        self._edits["smsbower.max_price"].setPlaceholderText("0.054")
        price_row.addWidget(QLabel("最低"))
        price_row.addWidget(self._edits["smsbower.min_price"])
        price_row.addWidget(QLabel("目标"))
        price_row.addWidget(self._edits["smsbower.target_price"])
        price_row.addWidget(QLabel("最高"))
        price_row.addWidget(self._edits["smsbower.max_price"])
        form.addRow("价格", price_row)

        self._edits["smsbower.sms_timeout"] = QSpinBox()
        self._edits["smsbower.sms_timeout"].setRange(30, 600)
        self._edits["smsbower.sms_timeout"].setSuffix(" 秒")
        form.addRow("短信超时", self._edits["smsbower.sms_timeout"])

        self._edits["smsbower.sms_poll_interval"] = QSpinBox()
        self._edits["smsbower.sms_poll_interval"].setRange(1, 60)
        self._edits["smsbower.sms_poll_interval"].setSuffix(" 秒")
        form.addRow("轮询间隔", self._edits["smsbower.sms_poll_interval"])

        self._edits["smsbower.number_attempts"] = QSpinBox()
        self._edits["smsbower.number_attempts"].setRange(1, 20)
        form.addRow("获取号码尝试", self._edits["smsbower.number_attempts"])

        # --- Phone reuse ---
        reuse_title = QLabel("手机号复用设置")
        reuse_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", reuse_title)

        self._edits["phone_reuse.max_reuse_count"] = QSpinBox()
        self._edits["phone_reuse.max_reuse_count"].setRange(1, 20)
        form.addRow("最大复用次数", self._edits["phone_reuse.max_reuse_count"])

        self._edits["phone_reuse.send_cooldown_seconds"] = QSpinBox()
        self._edits["phone_reuse.send_cooldown_seconds"].setRange(5, 300)
        self._edits["phone_reuse.send_cooldown_seconds"].setSuffix(" 秒")
        form.addRow("发送冷却", self._edits["phone_reuse.send_cooldown_seconds"])

        self._edits["phone_reuse.send_retry_attempts"] = QSpinBox()
        self._edits["phone_reuse.send_retry_attempts"].setRange(1, 20)
        form.addRow("发送重试次数", self._edits["phone_reuse.send_retry_attempts"])

        self._edits["phone_reuse.send_retry_delay_seconds"] = QSpinBox()
        self._edits["phone_reuse.send_retry_delay_seconds"].setRange(5, 300)
        self._edits["phone_reuse.send_retry_delay_seconds"].setSuffix(" 秒")
        form.addRow("发送重试延迟", self._edits["phone_reuse.send_retry_delay_seconds"])

        self._edits["phone_reuse.proxy"] = QLineEdit()
        self._edits["phone_reuse.proxy"].setPlaceholderText("http://127.0.0.1:7897")
        form.addRow("接码代理", self._edits["phone_reuse.proxy"])

        self._edits["phone_reuse.proxy_match_phone_country"] = QCheckBox("代理匹配手机国家")
        form.addRow("", self._edits["phone_reuse.proxy_match_phone_country"])

        self._edits["phone_reuse.proxy_random_sid"] = QCheckBox("随机代理会话")
        form.addRow("", self._edits["phone_reuse.proxy_random_sid"])

        layout.addLayout(form)
        layout.addStretch(1)
        return self._scroll_wrap(root)

    # ========== Registration tab ==========
    def _build_registration_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        # Password
        pwd_title = QLabel("密码生成")
        pwd_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")
        form.addRow("", pwd_title)

        self._edits["registration.password_random_length"] = QSpinBox()
        self._edits["registration.password_random_length"].setRange(8, 32)
        form.addRow("密码长度", self._edits["registration.password_random_length"])

        self._edits["registration.password_suffix"] = QLineEdit()
        self._edits["registration.password_suffix"].setPlaceholderText("!A1")
        form.addRow("密码后缀", self._edits["registration.password_suffix"])

        # Retry
        retry_title = QLabel("重试策略")
        retry_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", retry_title)

        self._edits["registration.retry_attempts"] = QSpinBox()
        self._edits["registration.retry_attempts"].setRange(0, 20)
        form.addRow("重试次数", self._edits["registration.retry_attempts"])

        self._edits["registration.retry_delay_seconds"] = QSpinBox()
        self._edits["registration.retry_delay_seconds"].setRange(0, 60)
        self._edits["registration.retry_delay_seconds"].setSuffix(" 秒")
        form.addRow("重试延迟", self._edits["registration.retry_delay_seconds"])

        # AT probe
        at_title = QLabel("AT 稳定性探测")
        at_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", at_title)

        self._edits["registration.at_stability_probe_count"] = QSpinBox()
        self._edits["registration.at_stability_probe_count"].setRange(0, 20)
        form.addRow("探测次数", self._edits["registration.at_stability_probe_count"])

        self._edits["registration.at_stability_probe_delay_seconds"] = QSpinBox()
        self._edits["registration.at_stability_probe_delay_seconds"].setRange(1, 120)
        self._edits["registration.at_stability_probe_delay_seconds"].setSuffix(" 秒")
        form.addRow("探测间隔", self._edits["registration.at_stability_probe_delay_seconds"])

        self._edits["registration.at_probe_timeout_seconds"] = QSpinBox()
        self._edits["registration.at_probe_timeout_seconds"].setRange(5, 120)
        self._edits["registration.at_probe_timeout_seconds"].setSuffix(" 秒")
        form.addRow("探测超时", self._edits["registration.at_probe_timeout_seconds"])

        # Sentinel
        sent_title = QLabel("Sentinel 并发控制")
        sent_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", sent_title)

        self._edits["email_registration.sentinel_max_concurrency"] = QSpinBox()
        self._edits["email_registration.sentinel_max_concurrency"].setRange(1, 20)
        form.addRow("最大并发", self._edits["email_registration.sentinel_max_concurrency"])

        self._edits["email_registration.sentinel_prewarm_window"] = QSpinBox()
        self._edits["email_registration.sentinel_prewarm_window"].setRange(0, 20)
        form.addRow("预热窗口", self._edits["email_registration.sentinel_prewarm_window"])

        self._edits["email_registration.sentinel_circuit_failures"] = QSpinBox()
        self._edits["email_registration.sentinel_circuit_failures"].setRange(1, 20)
        form.addRow("熔断阈值", self._edits["email_registration.sentinel_circuit_failures"])

        self._edits["email_registration.sentinel_circuit_cooldown_seconds"] = QSpinBox()
        self._edits["email_registration.sentinel_circuit_cooldown_seconds"].setRange(10, 600)
        self._edits["email_registration.sentinel_circuit_cooldown_seconds"].setSuffix(" 秒")
        form.addRow("熔断冷却", self._edits["email_registration.sentinel_circuit_cooldown_seconds"])

        # OTP
        otp_title = QLabel("OTP 轮询")
        otp_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", otp_title)

        self._edits["email_registration.otp_poll_interval"] = QSpinBox()
        self._edits["email_registration.otp_poll_interval"].setRange(1, 30)
        self._edits["email_registration.otp_poll_interval"].setSuffix(" 秒")
        form.addRow("OTP 轮询间隔", self._edits["email_registration.otp_poll_interval"])

        layout.addLayout(form)
        layout.addStretch(1)
        return self._scroll_wrap(root)

    # ========== Mail / Remail / CFWorker tab ==========
    def _build_mail_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        # --- Remail ---
        rm_title = QLabel("ReMail 长效邮箱")
        rm_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")
        form.addRow("", rm_title)

        self._edits["remail.enabled"] = QCheckBox("启用 ReMail")
        form.addRow("", self._edits["remail.enabled"])

        self._edits["remail.base_url"] = QLineEdit()
        self._edits["remail.base_url"].setPlaceholderText("https://remail.aishop6.com")
        form.addRow("API 地址", self._edits["remail.base_url"])

        self._edits["remail.api_key"] = QLineEdit()
        self._edits["remail.api_key"].setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key", self._edits["remail.api_key"])

        self._edits["remail.project_id"] = QSpinBox()
        self._edits["remail.project_id"].setRange(1, 999)
        form.addRow("项目 ID", self._edits["remail.project_id"])

        self._edits["remail.product_id"] = QSpinBox()
        self._edits["remail.product_id"].setRange(1, 999)
        form.addRow("产品 ID", self._edits["remail.product_id"])

        self._edits["remail.email_suffix"] = QLineEdit()
        self._edits["remail.email_suffix"].setPlaceholderText("outlook.com")
        form.addRow("邮箱后缀", self._edits["remail.email_suffix"])

        self._edits["remail.supplier_dead_rate_stop_threshold"] = QSpinBox()
        self._edits["remail.supplier_dead_rate_stop_threshold"].setRange(0, 100)
        self._edits["remail.supplier_dead_rate_stop_threshold"].setSuffix(" %")
        self._edits["remail.supplier_dead_rate_stop_threshold"].setValue(25)
        form.addRow("死号率停止阈值", self._edits["remail.supplier_dead_rate_stop_threshold"])

        self._edits["remail.batch_timeout"] = QSpinBox()
        self._edits["remail.batch_timeout"].setRange(30, 600)
        self._edits["remail.batch_timeout"].setSuffix(" 秒")
        form.addRow("批次超时", self._edits["remail.batch_timeout"])

        self._edits["remail.otp_poll_interval"] = QSpinBox()
        self._edits["remail.otp_poll_interval"].setRange(1, 30)
        self._edits["remail.otp_poll_interval"].setSuffix(" 秒")
        form.addRow("OTP 轮询间隔", self._edits["remail.otp_poll_interval"])

        # --- CFWorker ---
        cf_title = QLabel("CFWorker 邮箱")
        cf_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", cf_title)

        self._edits["cfworker.domain"] = QLineEdit()
        self._edits["cfworker.domain"].setPlaceholderText("mail.example.com")
        form.addRow("邮箱域名", self._edits["cfworker.domain"])

        self._edits["cfworker.url"] = QLineEdit()
        self._edits["cfworker.url"].setPlaceholderText("https://tempmail.example.com")
        form.addRow("API 地址", self._edits["cfworker.url"])

        self._edits["cfworker.admin_token"] = QLineEdit()
        self._edits["cfworker.admin_token"].setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Admin Token", self._edits["cfworker.admin_token"])

        self._edits["cfworker.api_token"] = QLineEdit()
        self._edits["cfworker.api_token"].setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Token", self._edits["cfworker.api_token"])

        self._edits["cfworker.timeout_seconds"] = QSpinBox()
        self._edits["cfworker.timeout_seconds"].setRange(10, 120)
        self._edits["cfworker.timeout_seconds"].setSuffix(" 秒")
        form.addRow("超时", self._edits["cfworker.timeout_seconds"])

        self._edits["cfworker.otp_settle_seconds"] = QSpinBox()
        self._edits["cfworker.otp_settle_seconds"].setRange(0, 30)
        self._edits["cfworker.otp_settle_seconds"].setSuffix(" 秒")
        form.addRow("OTP 沉淀时间", self._edits["cfworker.otp_settle_seconds"])

        self._edits["cfworker.poll_proxy"] = QCheckBox("通过代理轮询")
        form.addRow("", self._edits["cfworker.poll_proxy"])

        self._edits["cfworker.direct_fallback"] = QCheckBox("直连回退")
        form.addRow("", self._edits["cfworker.direct_fallback"])

        # --- Chongzhi ---
        cz_title = QLabel("Chongzhi 邮箱池")
        cz_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", cz_title)

        self._edits["chongzhi.enabled"] = QCheckBox("启用 Chongzhi")
        form.addRow("", self._edits["chongzhi.enabled"])

        self._edits["chongzhi.api_url"] = QLineEdit()
        self._edits["chongzhi.api_url"].setPlaceholderText("https://www.chongzhi.art/api/mailbox/fetch")
        form.addRow("API 地址", self._edits["chongzhi.api_url"])

        self._edits["chongzhi.rate_limit_seconds"] = QSpinBox()
        self._edits["chongzhi.rate_limit_seconds"].setRange(1, 300)
        self._edits["chongzhi.rate_limit_seconds"].setSuffix(" 秒")
        form.addRow("限流间隔", self._edits["chongzhi.rate_limit_seconds"])

        self._edits["chongzhi.timeout"] = QSpinBox()
        self._edits["chongzhi.timeout"].setRange(5, 120)
        self._edits["chongzhi.timeout"].setSuffix(" 秒")
        form.addRow("请求超时", self._edits["chongzhi.timeout"])

        layout.addLayout(form)
        layout.addStretch(1)
        return self._scroll_wrap(root)

    # ========== Other tab ==========
    def _build_other_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        oa_title = QLabel("OAuth / 认证指纹")
        oa_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")
        form.addRow("", oa_title)

        self._edits["email_registration.oauth_client_id"] = QLineEdit()
        form.addRow("OAuth Client ID", self._edits["email_registration.oauth_client_id"])

        self._edits["email_registration.oauth_scope"] = QLineEdit()
        form.addRow("OAuth 作用域", self._edits["email_registration.oauth_scope"])

        self._edits["email_registration.auth_fingerprint.mode"] = QComboBox()
        self._edits["email_registration.auth_fingerprint.mode"].addItems(["rotate", "fixed", "random"])
        self._combo_edits["email_registration.auth_fingerprint.mode"] = self._edits["email_registration.auth_fingerprint.mode"]
        form.addRow("指纹模式", self._edits["email_registration.auth_fingerprint.mode"])

        self._edits["email_registration.auth_fingerprint.profiles"] = QLineEdit()
        self._edits["email_registration.auth_fingerprint.profiles"].setPlaceholderText("chrome124, chrome131, chrome136")
        form.addRow("指纹配置", self._edits["email_registration.auth_fingerprint.profiles"])

        # Timeouts
        to_title = QLabel("超时设置")
        to_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", to_title)

        self._edits["timeouts.request"] = QSpinBox()
        self._edits["timeouts.request"].setRange(5, 120)
        self._edits["timeouts.request"].setSuffix(" 秒")
        form.addRow("请求超时", self._edits["timeouts.request"])

        self._edits["timeouts.http_retries"] = QSpinBox()
        self._edits["timeouts.http_retries"].setRange(0, 20)
        form.addRow("HTTP 重试", self._edits["timeouts.http_retries"])

        self._edits["timeouts.retry_delay"] = QSpinBox()
        self._edits["timeouts.retry_delay"].setRange(0, 30)
        self._edits["timeouts.retry_delay"].setSuffix(" 秒")
        form.addRow("重试延迟", self._edits["timeouts.retry_delay"])

        self._edits["timeouts.token_cache_ttl"] = QSpinBox()
        self._edits["timeouts.token_cache_ttl"].setRange(30, 3600)
        self._edits["timeouts.token_cache_ttl"].setSuffix(" 秒")
        form.addRow("Token 缓存 TTL", self._edits["timeouts.token_cache_ttl"])

        # Codex OAuth
        co_title = QLabel("Codex OAuth")
        co_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 12px;")
        form.addRow("", co_title)

        self._edits["codex_oauth.registration_timeout"] = QSpinBox()
        self._edits["codex_oauth.registration_timeout"].setRange(30, 600)
        self._edits["codex_oauth.registration_timeout"].setSuffix(" 秒")
        form.addRow("注册超时", self._edits["codex_oauth.registration_timeout"])

        self._edits["codex_oauth.allow_passwordless_takeover"] = QCheckBox("允许无密码接管")
        form.addRow("", self._edits["codex_oauth.allow_passwordless_takeover"])

        self._edits["codex_oauth.auto_phone_verification"] = QCheckBox("自动手机验证")
        form.addRow("", self._edits["codex_oauth.auto_phone_verification"])

        layout.addLayout(form)
        layout.addStretch(1)
        return self._scroll_wrap(root)

    # ========== Load ==========
    def _load(self) -> None:
        try:
            self._config = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except Exception:
            self._config = {}

        cfg = self._config

        # Proxy
        proxy = cfg.get("proxy", {})
        self._set_text("proxy.registration", proxy.get("registration", ""))
        self._set_text("proxy.default", proxy.get("default", ""))
        pool = proxy.get("pool", [])
        if isinstance(pool, list):
            self._set_text("proxy.pool", ", ".join(str(p) for p in pool))
        else:
            self._set_text("proxy.pool", str(pool))
        self._set_text("mailbox_proxy", cfg.get("mailbox_proxy", ""))

        # SMSBower
        pr = cfg.get("phone_reuse", {})
        sms = pr.get("smsbower", {})
        self._set_text("smsbower.api_key", sms.get("api_key", ""))
        self._set_text("smsbower.service", sms.get("service", ""))
        self._set_text("smsbower.service_name", sms.get("service_name", ""))
        self._set_text("smsbower.country", sms.get("country", ""))
        self._set_text("smsbower.country_name", sms.get("country_name", ""))
        self._set_text("smsbower.country_prefix", sms.get("country_prefix", ""))
        self._set_text("smsbower.min_price", sms.get("min_price", ""))
        self._set_text("smsbower.target_price", sms.get("target_price", ""))
        self._set_text("smsbower.max_price", sms.get("max_price", ""))
        self._set_int("smsbower.sms_timeout", sms.get("sms_timeout", 120))
        self._set_int("smsbower.sms_poll_interval", sms.get("sms_poll_interval", 5))
        self._set_int("smsbower.number_attempts", sms.get("number_attempts", 3))

        # Phone reuse
        self._set_int("phone_reuse.max_reuse_count", pr.get("max_reuse_count", 1))
        self._set_int("phone_reuse.send_cooldown_seconds", pr.get("send_cooldown_seconds", 45))
        self._set_int("phone_reuse.send_retry_attempts", pr.get("send_retry_attempts", 3))
        self._set_int("phone_reuse.send_retry_delay_seconds", pr.get("send_retry_delay_seconds", 45))
        self._set_text("phone_reuse.proxy", pr.get("proxy", ""))
        self._set_check("phone_reuse.proxy_match_phone_country", pr.get("proxy_match_phone_country", False))
        self._set_check("phone_reuse.proxy_random_sid", pr.get("proxy_random_sid", False))

        # Registration
        reg = cfg.get("registration", {})
        self._set_int("registration.password_random_length", reg.get("password_random_length", 12))
        self._set_text("registration.password_suffix", reg.get("password_suffix", ""))
        self._set_int("registration.retry_attempts", reg.get("retry_attempts", 2))
        self._set_int("registration.retry_delay_seconds", reg.get("retry_delay_seconds", 1))
        self._set_int("registration.at_stability_probe_count", reg.get("at_stability_probe_count", 2))
        self._set_int("registration.at_stability_probe_delay_seconds", reg.get("at_stability_probe_delay_seconds", 10))
        self._set_int("registration.at_probe_timeout_seconds", reg.get("at_probe_timeout_seconds", 30))

        # Remail
        er = cfg.get("email_registration", {})
        rm = er.get("remail", {})
        self._set_check("remail.enabled", rm.get("enabled", False))
        self._set_text("remail.base_url", rm.get("base_url", ""))
        self._set_text("remail.api_key", rm.get("api_key", ""))
        self._set_int("remail.project_id", rm.get("project_id", 2))
        self._set_int("remail.product_id", rm.get("product_id", 5))
        self._set_text("remail.email_suffix", rm.get("email_suffix", ""))
        self._set_int("remail.supplier_dead_rate_stop_threshold", int(rm.get("supplier_dead_rate_stop_threshold", 0.25) * 100))
        self._set_int("remail.batch_timeout", rm.get("batch_timeout", 200))
        self._set_int("remail.otp_poll_interval", rm.get("otp_poll_interval", 1))

        # CFWorker
        self._set_text("cfworker.domain", er.get("cfworker_domain", ""))
        self._set_text("cfworker.url", er.get("cfworker_url", ""))
        self._set_text("cfworker.admin_token", er.get("cfworker_admin_token", ""))
        self._set_text("cfworker.api_token", er.get("cfworker_api_token", ""))
        self._set_int("cfworker.timeout_seconds", er.get("cfworker_timeout_seconds", 30))
        self._set_int("cfworker.otp_settle_seconds", er.get("cfworker_otp_settle_seconds", 3))
        self._set_check("cfworker.poll_proxy", er.get("cfworker_poll_proxy", True))
        self._set_check("cfworker.direct_fallback", er.get("cfworker_direct_fallback", False))

        # Chongzhi
        cz = er.get("chongzhi", {})
        self._set_check("chongzhi.enabled", cz.get("enabled", True))
        self._set_text("chongzhi.api_url", cz.get("api_url", ""))
        self._set_int("chongzhi.rate_limit_seconds", cz.get("rate_limit_seconds", 32))
        self._set_int("chongzhi.timeout", cz.get("timeout", 30))

        # Sentinel
        self._set_int("email_registration.sentinel_max_concurrency", er.get("sentinel_max_concurrency", 2))
        self._set_int("email_registration.sentinel_prewarm_window", er.get("sentinel_prewarm_window", 4))
        self._set_int("email_registration.sentinel_circuit_failures", er.get("sentinel_circuit_failures", 3))
        self._set_int("email_registration.sentinel_circuit_cooldown_seconds", er.get("sentinel_circuit_cooldown_seconds", 60))
        self._set_int("email_registration.otp_poll_interval", er.get("otp_poll_interval", 2))

        # OAuth
        self._set_text("email_registration.oauth_client_id", er.get("oauth_client_id", ""))
        self._set_text("email_registration.oauth_scope", er.get("oauth_scope", ""))
        mode = er.get("auth_fingerprint", {}).get("mode", "rotate")
        self._set_combo("email_registration.auth_fingerprint.mode", mode)
        profiles = er.get("auth_fingerprint", {}).get("profiles", [])
        self._set_text("email_registration.auth_fingerprint.profiles", ", ".join(profiles))

        # Timeouts
        to = cfg.get("timeouts", {})
        self._set_int("timeouts.request", to.get("request", 20))
        self._set_int("timeouts.http_retries", to.get("http_retries", 3))
        self._set_int("timeouts.retry_delay", to.get("retry_delay", 2))
        self._set_int("timeouts.token_cache_ttl", to.get("token_cache_ttl", 300))

        # Codex OAuth
        co = cfg.get("codex_oauth", {})
        self._set_int("codex_oauth.registration_timeout", co.get("registration_timeout", 180))
        self._set_check("codex_oauth.allow_passwordless_takeover", co.get("allow_passwordless_takeover", False))
        self._set_check("codex_oauth.auto_phone_verification", co.get("auto_phone_verification", False))

    # ========== Save ==========
    def _on_proxy_pool_changed(self) -> None:
        w = self._edits.get("proxy.pool")
        if not isinstance(w, QPlainTextEdit):
            return
        text = w.toPlainText()
        if "\n" in text or "\r" in text:
            lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
            if lines:
                w.blockSignals(True)
                w.setPlainText(", ".join(lines))
                w.blockSignals(False)

    def _save(self) -> None:
        cfg = self._config

        # Proxy
        proxy = cfg.setdefault("proxy", {})
        proxy["registration"] = self._get_text("proxy.registration")
        proxy["default"] = self._get_text("proxy.default")
        raw = self._get_text("proxy.pool")
        proxy["pool"] = [p.strip() for p in raw.split(",") if p.strip()]
        cfg["mailbox_proxy"] = self._get_text("mailbox_proxy")

        # SMSBower
        pr = cfg.setdefault("phone_reuse", {})
        sms = pr.setdefault("smsbower", {})
        sms["api_key"] = self._get_text("smsbower.api_key")
        sms["service"] = self._get_text("smsbower.service")
        sms["service_name"] = self._get_text("smsbower.service_name")
        sms["country"] = self._get_text("smsbower.country")
        sms["country_name"] = self._get_text("smsbower.country_name")
        sms["country_prefix"] = self._get_text("smsbower.country_prefix")
        sms["min_price"] = self._get_text("smsbower.min_price")
        sms["target_price"] = self._get_text("smsbower.target_price")
        sms["max_price"] = self._get_text("smsbower.max_price")
        sms["sms_timeout"] = self._get_int("smsbower.sms_timeout")
        sms["sms_poll_interval"] = self._get_int("smsbower.sms_poll_interval")
        sms["number_attempts"] = self._get_int("smsbower.number_attempts")

        # Phone reuse
        pr["max_reuse_count"] = self._get_int("phone_reuse.max_reuse_count")
        pr["send_cooldown_seconds"] = self._get_int("phone_reuse.send_cooldown_seconds")
        pr["send_retry_attempts"] = self._get_int("phone_reuse.send_retry_attempts")
        pr["send_retry_delay_seconds"] = self._get_int("phone_reuse.send_retry_delay_seconds")
        pr["proxy"] = self._get_text("phone_reuse.proxy")
        pr["proxy_match_phone_country"] = self._get_check("phone_reuse.proxy_match_phone_country")
        pr["proxy_random_sid"] = self._get_check("phone_reuse.proxy_random_sid")

        # Registration
        reg = cfg.setdefault("registration", {})
        reg["password_random_length"] = self._get_int("registration.password_random_length")
        reg["password_suffix"] = self._get_text("registration.password_suffix")
        reg["retry_attempts"] = self._get_int("registration.retry_attempts")
        reg["retry_delay_seconds"] = self._get_int("registration.retry_delay_seconds")
        reg["at_stability_probe_count"] = self._get_int("registration.at_stability_probe_count")
        reg["at_stability_probe_delay_seconds"] = self._get_int("registration.at_stability_probe_delay_seconds")
        reg["at_probe_timeout_seconds"] = self._get_int("registration.at_probe_timeout_seconds")

        # Remail
        er = cfg.setdefault("email_registration", {})
        rm = er.setdefault("remail", {})
        rm["enabled"] = self._get_check("remail.enabled")
        rm["base_url"] = self._get_text("remail.base_url")
        rm["api_key"] = self._get_text("remail.api_key")
        rm["project_id"] = self._get_int("remail.project_id")
        rm["product_id"] = self._get_int("remail.product_id")
        rm["email_suffix"] = self._get_text("remail.email_suffix")
        rm["supplier_dead_rate_stop_threshold"] = self._get_int("remail.supplier_dead_rate_stop_threshold") / 100.0
        rm["batch_timeout"] = self._get_int("remail.batch_timeout")
        rm["otp_poll_interval"] = self._get_int("remail.otp_poll_interval")

        # CFWorker
        er["cfworker_domain"] = self._get_text("cfworker.domain")
        er["cfworker_url"] = self._get_text("cfworker.url")
        er["cfworker_admin_token"] = self._get_text("cfworker.admin_token")
        er["cfworker_api_token"] = self._get_text("cfworker.api_token")
        er["cfworker_timeout_seconds"] = self._get_int("cfworker.timeout_seconds")
        er["cfworker_otp_settle_seconds"] = self._get_int("cfworker.otp_settle_seconds")
        er["cfworker_poll_proxy"] = self._get_check("cfworker.poll_proxy")
        er["cfworker_direct_fallback"] = self._get_check("cfworker.direct_fallback")

        # Chongzhi
        cz = er.setdefault("chongzhi", {})
        cz["enabled"] = self._get_check("chongzhi.enabled")
        cz["api_url"] = self._get_text("chongzhi.api_url")
        cz["rate_limit_seconds"] = self._get_int("chongzhi.rate_limit_seconds")
        cz["timeout"] = self._get_int("chongzhi.timeout")

        # Sentinel
        er["sentinel_max_concurrency"] = self._get_int("email_registration.sentinel_max_concurrency")
        er["sentinel_prewarm_window"] = self._get_int("email_registration.sentinel_prewarm_window")
        er["sentinel_circuit_failures"] = self._get_int("email_registration.sentinel_circuit_failures")
        er["sentinel_circuit_cooldown_seconds"] = self._get_int("email_registration.sentinel_circuit_cooldown_seconds")
        er["otp_poll_interval"] = self._get_int("email_registration.otp_poll_interval")

        # OAuth
        er["oauth_client_id"] = self._get_text("email_registration.oauth_client_id")
        er["oauth_scope"] = self._get_text("email_registration.oauth_scope")
        fp = er.setdefault("auth_fingerprint", {})
        fp["mode"] = self._get_combo("email_registration.auth_fingerprint.mode")
        raw_profiles = self._get_text("email_registration.auth_fingerprint.profiles")
        fp["profiles"] = [p.strip() for p in raw_profiles.split(",") if p.strip()]

        # Timeouts
        to = cfg.setdefault("timeouts", {})
        to["request"] = self._get_int("timeouts.request")
        to["http_retries"] = self._get_int("timeouts.http_retries")
        to["retry_delay"] = self._get_int("timeouts.retry_delay")
        to["token_cache_ttl"] = self._get_int("timeouts.token_cache_ttl")

        # Codex OAuth
        co = cfg.setdefault("codex_oauth", {})
        co["registration_timeout"] = self._get_int("codex_oauth.registration_timeout")
        co["allow_passwordless_takeover"] = self._get_check("codex_oauth.allow_passwordless_takeover")
        co["auto_phone_verification"] = self._get_check("codex_oauth.auto_phone_verification")

        try:
            self.config_path.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            QMessageBox.information(self, "保存成功", "配置已保存到 config.json")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    # ========== Helpers ==========
    def _set_text(self, key: str, value: str) -> None:
        w = self._edits.get(key)
        if isinstance(w, QLineEdit):
            w.setText(str(value))
        elif isinstance(w, QPlainTextEdit):
            w.setPlainText(str(value))

    def _set_int(self, key: str, value: int) -> None:
        w = self._edits.get(key)
        if isinstance(w, QSpinBox):
            w.setValue(int(value))

    def _set_check(self, key: str, value: bool) -> None:
        w = self._edits.get(key)
        if isinstance(w, QCheckBox):
            w.setChecked(bool(value))

    def _set_combo(self, key: str, value: str) -> None:
        w = self._combo_edits.get(key)
        if isinstance(w, QComboBox):
            idx = w.findText(str(value), Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                w.setCurrentIndex(idx)

    def _get_text(self, key: str) -> str:
        w = self._edits.get(key)
        if isinstance(w, QLineEdit):
            return str(w.text()).strip()
        if isinstance(w, QPlainTextEdit):
            return str(w.toPlainText()).strip()
        return ""

    def _get_int(self, key: str) -> int:
        w = self._edits.get(key)
        return w.value() if isinstance(w, QSpinBox) else 0

    def _get_check(self, key: str) -> bool:
        w = self._edits.get(key)
        return w.isChecked() if isinstance(w, QCheckBox) else False

    def _get_combo(self, key: str) -> str:
        w = self._combo_edits.get(key)
        return str(w.currentText()) if isinstance(w, QComboBox) else ""

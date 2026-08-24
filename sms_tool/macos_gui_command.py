"""Qt-free command construction for the macOS registration workbench."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SOURCES = {"pool", "remail", "cfworker", "phone", "explicit"}


@dataclass(frozen=True)
class RegistrationGuiOptions:
    source: str = "pool"
    count: int = 1
    workers: int = 1
    mailbox_file: str = ""
    mailbox_text: str = ""
    email: str = ""
    email_password: str = ""
    email_refresh_token: str = ""
    email_access_token: str = ""
    remail_token: str = ""
    cfworker_domain: str = ""
    smsbower_country: str = ""
    proxy: str = ""
    proxy_pool: str = ""
    account_password: str = ""
    registration_mode: str = ""
    registration_at_only: bool = True
    disable_phone_verification: bool = True


def validate_options(options: RegistrationGuiOptions) -> list[str]:
    errors: list[str] = []
    source = options.source.strip().lower()
    if source not in SUPPORTED_SOURCES:
        errors.append(f"不支持的注册方式：{options.source}")
    if not 1 <= options.count <= 200:
        errors.append("注册数量必须在 1 到 200 之间。")
    if not 1 <= options.workers <= 20:
        errors.append("并发数必须在 1 到 20 之间。")

    if source == "pool":
        if options.mailbox_text.strip():
            pass
        else:
            mailbox_file = Path(options.mailbox_file).expanduser()
            if not options.mailbox_file.strip() or not mailbox_file.is_file():
                errors.append("邮箱池内容为空，或邮箱文件不存在。")
    elif source == "cfworker" and not options.cfworker_domain.strip():
        errors.append("CFWorker 注册需要填写邮箱域名。")
    elif source == "explicit":
        if not options.email.strip():
            errors.append("单邮箱注册需要填写邮箱地址。")
        if not any(
            value.strip()
            for value in (
                options.email_password,
                options.email_refresh_token,
                options.email_access_token,
                options.remail_token,
            )
        ):
            errors.append("单邮箱注册至少需要密码、Refresh Token、Access Token 或 ReMail Token。")
    return errors


def _append_value(args: list[str], flag: str, value: str) -> None:
    value = str(value or "").strip()
    if value:
        args.extend((flag, value))


def build_registration_args(options: RegistrationGuiOptions) -> list[str]:
    errors = validate_options(options)
    if errors:
        raise ValueError("\n".join(errors))

    source = options.source.strip().lower()
    args: list[str] = []
    if source == "pool":
        args.extend(("--chatai-mailbox-file", str(Path(options.mailbox_file).expanduser())))
        args.extend(("--count", str(options.count), "--workers", str(options.workers)))
    elif source == "remail":
        args.extend(
            (
                "--target-at200",
                str(options.count),
                "--buy-remail-mailbox",
                "--remail-service-mode",
                "purchase",
                "--workers",
                str(options.workers),
            )
        )
    elif source == "cfworker":
        args.extend(
            (
                "--buy-cfworker-mailbox",
                "--cfworker-domain",
                options.cfworker_domain.strip(),
                "--count",
                str(options.count),
                "--workers",
                str(options.workers),
            )
        )
    elif source == "phone":
        args.extend(("--phone-register", "--count", str(options.count)))
        _append_value(args, "--smsbower-country", options.smsbower_country)
    elif source == "explicit":
        _append_value(args, "--email", options.email)
        _append_value(args, "--email-password", options.email_password)
        _append_value(args, "--email-refresh-token", options.email_refresh_token)
        _append_value(args, "--email-access-token", options.email_access_token)
        _append_value(args, "--remail-token", options.remail_token)
        args.extend(("--count", str(options.count), "--workers", str(options.workers)))

    if options.registration_at_only:
        args.append("--registration-at-only")
    if source != "phone" and (options.disable_phone_verification or options.registration_at_only):
        args.append("--no-phone-reuse")
    _append_value(args, "--proxy", options.proxy)
    _append_value(args, "--proxy-pool", options.proxy_pool)
    _append_value(args, "--password", options.account_password)
    _append_value(args, "--registration-mode", options.registration_mode)
    return args

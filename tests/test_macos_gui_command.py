from sms_tool.macos_gui_command import (
    RegistrationGuiOptions,
    build_registration_args,
    validate_options,
)


def test_pool_source_builds_existing_chatai_registration_command(tmp_path):
    mailbox_file = tmp_path / "mailboxes.txt"
    mailbox_file.write_text("user@example.com----password----client----refresh\n", encoding="utf-8")
    options = RegistrationGuiOptions(
        source="pool",
        mailbox_file=str(mailbox_file),
        count=3,
        workers=2,
        proxy="http://127.0.0.1:7897",
        registration_at_only=True,
    )

    assert validate_options(options) == []
    assert build_registration_args(options) == [
        "--chatai-mailbox-file",
        str(mailbox_file),
        "--count",
        "3",
        "--workers",
        "2",
        "--registration-at-only",
        "--no-phone-reuse",
        "--proxy",
        "http://127.0.0.1:7897",
    ]


def test_remail_source_builds_bounded_stable_at_target_command():
    options = RegistrationGuiOptions(source="remail", count=5, workers=3)

    assert validate_options(options) == []
    assert build_registration_args(options) == [
        "--target-at200",
        "5",
        "--buy-remail-mailbox",
        "--remail-service-mode",
        "purchase",
        "--workers",
        "3",
        "--registration-at-only",
        "--no-phone-reuse",
    ]


def test_cfworker_source_requires_domain_and_builds_command():
    missing = RegistrationGuiOptions(source="cfworker", cfworker_domain="")
    assert validate_options(missing) == ["CFWorker 注册需要填写邮箱域名。"]

    options = RegistrationGuiOptions(
        source="cfworker",
        cfworker_domain="mail.example.com",
        count=4,
        workers=2,
        registration_at_only=False,
        disable_phone_verification=True,
    )
    assert validate_options(options) == []
    assert build_registration_args(options) == [
        "--buy-cfworker-mailbox",
        "--cfworker-domain",
        "mail.example.com",
        "--count",
        "4",
        "--workers",
        "2",
        "--no-phone-reuse",
    ]


def test_phone_source_does_not_add_email_phone_reuse_flags():
    options = RegistrationGuiOptions(
        source="phone",
        count=2,
        workers=1,
        smsbower_country="6",
        registration_at_only=False,
        disable_phone_verification=False,
    )

    assert validate_options(options) == []
    assert build_registration_args(options) == [
        "--phone-register",
        "--count",
        "2",
        "--smsbower-country",
        "6",
    ]


def test_explicit_mailbox_builds_credentials_without_leaking_empty_values():
    options = RegistrationGuiOptions(
        source="explicit",
        email="user@example.com",
        email_password="mail-password",
        email_refresh_token="refresh-token",
        count=1,
        workers=1,
    )

    assert validate_options(options) == []
    assert build_registration_args(options) == [
        "--email",
        "user@example.com",
        "--email-password",
        "mail-password",
        "--email-refresh-token",
        "refresh-token",
        "--count",
        "1",
        "--workers",
        "1",
        "--registration-at-only",
        "--no-phone-reuse",
    ]


def test_validation_rejects_invalid_ranges_unknown_source_and_missing_file(tmp_path):
    options = RegistrationGuiOptions(
        source="mystery",
        count=0,
        workers=21,
        mailbox_file=str(tmp_path / "missing.txt"),
    )

    assert validate_options(options) == [
        "不支持的注册方式：mystery",
        "注册数量必须在 1 到 200 之间。",
        "并发数必须在 1 到 20 之间。",
    ]


def test_pool_validation_rejects_missing_mailbox_file(tmp_path):
    options = RegistrationGuiOptions(source="pool", mailbox_file=str(tmp_path / "missing.txt"))
    assert validate_options(options) == ["邮箱池内容为空，或邮箱文件不存在。"]


def test_pool_validation_accepts_pasted_mailbox_text():
    options = RegistrationGuiOptions(
        source="pool",
        mailbox_text="user@icloud.com----https://mail.example/inbox/private-token\n",
    )

    assert validate_options(options) == []

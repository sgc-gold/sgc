"""Read notification recipients without storing contact details in source code."""

import json
import os
from email.headerregistry import Address
from email.errors import HeaderParseError
from typing import Mapping, NamedTuple


class NotificationRecipients(NamedTuple):
    from_email: str
    to_email: str
    bcc_emails: tuple[str, ...]


def _mailbox(value: object, setting: str) -> str:
    if not isinstance(value, str) or "\r" in value or "\n" in value:
        raise ValueError(f"{setting} must contain a plain email address")
    value = value.strip()
    try:
        address = Address(addr_spec=value)
        if not address.username or not address.domain or address.addr_spec != value:
            raise ValueError
    except (ValueError, IndexError, HeaderParseError):
        # Never put the supplied address or parser exception in logs.
        raise ValueError(f"{setting} must contain a plain email address") from None
    return value


def load_notification_recipients(
    environ: Mapping[str, str] | None = None,
) -> NotificationRecipients:
    source = os.environ if environ is None else environ
    names = ("TANAKA_MAIL_FROM", "TANAKA_MAIL_TO", "TANAKA_MAIL_BCC")
    missing = [name for name in names if not source.get(name, "").strip()]
    if missing:
        raise ValueError("Missing notification settings: " + ", ".join(missing))
    try:
        bcc = json.loads(source["TANAKA_MAIL_BCC"])
    except (TypeError, ValueError):
        raise ValueError("TANAKA_MAIL_BCC must be a JSON array of email addresses") from None
    if not isinstance(bcc, list):
        raise ValueError("TANAKA_MAIL_BCC must be a JSON array of email addresses")
    return NotificationRecipients(
        _mailbox(source["TANAKA_MAIL_FROM"], "TANAKA_MAIL_FROM"),
        _mailbox(source["TANAKA_MAIL_TO"], "TANAKA_MAIL_TO"),
        tuple(_mailbox(value, "TANAKA_MAIL_BCC") for value in bcc),
    )


if __name__ == "__main__":
    try:
        load_notification_recipients()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print("Notification recipient configuration is valid")

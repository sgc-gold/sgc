"""Recipient and SMTP checks. No real delivery or top-level tanaka execution."""

import ast
import base64
import contextlib
import io
import os
from pathlib import Path
import smtplib
import sys
import tempfile
import unittest
from email import message_from_string
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from notification_config import load_notification_recipients


class RecipientTests(unittest.TestCase):
    def settings(self):
        return {
            "TANAKA_MAIL_FROM": "sender@example.invalid",
            "TANAKA_MAIL_TO": "team@example.invalid",
            "TANAKA_MAIL_BCC": '["one@example.invalid", "two@example.invalid"]',
        }

    def test_keeps_all_configured_recipients(self):
        parsed = load_notification_recipients(self.settings())
        self.assertEqual(parsed.from_email, "sender@example.invalid")
        self.assertEqual(parsed.to_email, "team@example.invalid")
        self.assertEqual(parsed.bcc_emails, ("one@example.invalid", "two@example.invalid"))

    def test_requires_each_setting_without_exposing_values(self):
        for key in self.settings():
            settings = self.settings()
            settings[key] = ""
            with self.subTest(key=key), self.assertRaises(ValueError) as caught:
                load_notification_recipients(settings)
            self.assertIn(key, str(caught.exception))
            self.assertNotIn("@", str(caught.exception))

    def test_rejects_header_injection_and_malformed_addresses(self):
        for value in ["one@example.invalid\r\nBcc: injected@example.invalid", "a@@example.invalid", "a", "<a@example.invalid>"]:
            for key in ["TANAKA_MAIL_FROM", "TANAKA_MAIL_TO", "TANAKA_MAIL_BCC"]:
                import json
                settings = self.settings()
                settings[key] = json.dumps([value]) if key.endswith("BCC") else value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError) as caught:
                    load_notification_recipients(settings)
                self.assertNotIn("@", str(caught.exception))

    def test_bcc_requires_an_explicit_json_array(self):
        for value in ['"one@example.invalid"', "null", "{}", "[null]", "one@example.invalid"]:
            settings = self.settings()
            settings["TANAKA_MAIL_BCC"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_notification_recipients(settings)
        settings["TANAKA_MAIL_BCC"] = "[]"
        self.assertEqual(load_notification_recipients(settings).bcc_emails, ())


class SmtpTests(unittest.TestCase):
    def setUp(self):
        # Import only the delivery function: tanaka.py also sends LINE WORKS at top level.
        tree = ast.parse((ROOT / "scripts/tanaka.py").read_text(encoding="utf-8"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "send_email_smtp")
        self.smtp = MagicMock()
        transport = MagicMock()
        transport.SMTP.return_value.__enter__.return_value = self.smtp
        transport.SMTPAuthenticationError = smtplib.SMTPAuthenticationError
        self.namespace = {
            "smtplib": transport, "os": os, "Header": Header,
            "MIMEImage": MIMEImage, "MIMEMultipart": MIMEMultipart, "MIMEText": MIMEText,
            "SMTP_HOST": "smtp.example.invalid", "SMTP_PORT": 587,
            "SMTP_USERNAME": "test-user", "SMTP_PASSWORD": "test-password",
            "FROM_EMAIL": "sender@example.invalid", "TO_EMAIL": "team@example.invalid",
            "BCC_EMAILS": ("one@example.invalid", "two@example.invalid"),
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(ROOT / "scripts/tanaka.py"), "exec"), self.namespace)

    def send(self, images=None):
        with contextlib.redirect_stdout(io.StringIO()):
            self.namespace["send_email_smtp"](subject="価格更新テスト", html_body="<p>test</p>", inline_images=images or {})

    def test_bcc_is_delivered_only_in_envelope(self):
        self.send()
        sender, recipients, raw = self.smtp.sendmail.call_args.args
        self.assertEqual(sender, "sender@example.invalid")
        self.assertEqual(recipients, ["team@example.invalid", "one@example.invalid", "two@example.invalid"])
        message = message_from_string(raw)
        self.assertIsNone(message["Bcc"])
        self.assertEqual(message["To"], "team@example.invalid")
        self.assertNotIn("one@example.invalid", raw)
        self.assertNotIn("two@example.invalid", raw)
        self.smtp.starttls.assert_called_once()
        self.smtp.login.assert_called_once_with("test-user", "test-password")

    def test_inline_chart_and_missing_image_behavior(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aBTsAAAAASUVORK5CYII=")
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "chart.png"
            image.write_bytes(png)
            self.send({"chart": str(image), "missing": str(image.with_name("missing.png"))})
        message = message_from_string(self.smtp.sendmail.call_args.args[2])
        images = [part for part in message.walk() if part.get_content_maintype() == "image"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["Content-ID"], "<chart>")

    def test_missing_smtp_or_failed_login_never_sends(self):
        self.namespace["SMTP_PASSWORD"] = ""
        with self.assertRaises(RuntimeError):
            self.send()
        self.namespace["SMTP_PASSWORD"] = "test-password"
        self.smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        with self.assertRaises(RuntimeError):
            self.send()
        self.smtp.sendmail.assert_not_called()


if __name__ == "__main__":
    unittest.main()

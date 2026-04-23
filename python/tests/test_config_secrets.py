"""Redaction + startup-secrets logging."""

import logging
from unittest.mock import patch

from config import log_redacted_secrets, redact


def test_redact_short_value():
    assert redact("abc") == "***"


def test_redact_long_value_keeps_prefix():
    assert redact("sk-ant-super-long-key") == "sk-a***"


def test_redact_empty():
    assert redact("") == "<unset>"


def test_log_redacted_secrets_never_emits_values(caplog):
    caplog.set_level(logging.INFO)
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-supersecret-123"}):
        log_redacted_secrets()
    message = caplog.text
    assert "sk-ant-supersecret-123" not in message
    assert "ANTHROPIC_API_KEY=set" in message


def test_log_redacted_secrets_reports_missing(caplog):
    caplog.set_level(logging.INFO)
    with patch.dict("os.environ", {}, clear=True):
        log_redacted_secrets()
    assert "ANTHROPIC_API_KEY=missing" in caplog.text

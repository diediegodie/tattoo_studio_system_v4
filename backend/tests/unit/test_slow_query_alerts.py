import itertools
from typing import Any, Dict, List

import pytest
from flask import Flask, g
from sqlalchemy import create_engine, text

from app.core import db as slow_db


@pytest.fixture(autouse=True)
def reset_module_state(monkeypatch):
    monkeypatch.setenv("ALERT_SLOW_QUERY_ENABLED", "true")
    monkeypatch.setenv("ALERT_QUERY_MS_THRESHOLD", "50")
    monkeypatch.setenv("ALERT_SINK_SLACK_WEBHOOK", "")
    slow_db._SLACK_FAILURES.clear()
    yield
    slow_db._SLACK_FAILURES.clear()


@pytest.fixture
def instrumented_engine():
    engine = create_engine("sqlite:///:memory:")
    slow_db.register_query_timing(engine)
    return engine


def _capture_logger_calls(monkeypatch) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    def record_warning(message: str, *args, **kwargs):
        records.append(
            {
                "message": message,
                "context": kwargs.get("extra", {}).get("context"),
            }
        )

    monkeypatch.setattr(slow_db.logger, "warning", record_warning)
    return records


def test_slow_query_alert_includes_request_context(monkeypatch, instrumented_engine):
    records = _capture_logger_calls(monkeypatch)
    slack_payloads: List[Dict[str, Any]] = []
    monkeypatch.setattr(
        slow_db,
        "_post_slack",
        lambda webhook, payload: slack_payloads.append(
            {"webhook": webhook, "payload": payload}
        ),
    )
    monkeypatch.setenv("ALERT_SINK_SLACK_WEBHOOK", "https://hooks.example")

    perf_values = itertools.cycle([1.0, 1.25])
    monkeypatch.setattr(slow_db.time, "perf_counter", lambda: next(perf_values))

    app = Flask(__name__)
    with app.test_request_context("/artists", method="GET"):
        g.request_id = "req-123"
        g.route = "artists.list"
        g.user_id = 42

        with instrumented_engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    assert len(records) == 1
    payload = records[0]["context"]
    assert payload["alert_type"] == "slow_query"
    assert payload["duration_ms"] == 250.0
    assert payload["context"]["request_id"] == "req-123"
    assert payload["context"]["route"] == "artists.list"
    assert payload["context"]["user_id"] == 42
    assert slack_payloads, "expected slack payload to be emitted"


def test_mask_sensitive_parameters(monkeypatch, instrumented_engine):
    records = _capture_logger_calls(monkeypatch)
    perf_values = itertools.cycle([1.0, 1.2])
    monkeypatch.setattr(slow_db.time, "perf_counter", lambda: next(perf_values))

    with instrumented_engine.connect() as conn:
        conn.execute(
            text("SELECT :email AS email, :password AS password"),
            {"email": "user@example.com", "password": "supersecret"},
        )

    assert len(records) == 1
    params = records[0]["context"]["params"]
    assert params["email"] == "***"
    assert params["password"] == "***"


def test_threshold_reflects_environment(monkeypatch, instrumented_engine):
    records = _capture_logger_calls(monkeypatch)
    perf_values = iter([1.0, 1.1, 2.0, 2.1])
    monkeypatch.setattr(slow_db.time, "perf_counter", lambda: next(perf_values))

    monkeypatch.setenv("ALERT_QUERY_MS_THRESHOLD", "150")
    with instrumented_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    assert not records

    monkeypatch.setenv("ALERT_QUERY_MS_THRESHOLD", "50")
    with instrumented_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    assert len(records) == 1


def test_slack_failure_only_logged_once(monkeypatch, instrumented_engine):
    error_calls: List[Dict[str, Any]] = []

    def record_error(message: str, *args, **kwargs):
        error_calls.append({"message": message, "context": kwargs.get("extra", {})})

    monkeypatch.setattr(slow_db.logger, "error", record_error)
    monkeypatch.setenv("ALERT_SINK_SLACK_WEBHOOK", "https://hooks.example")

    def fake_urlopen(*args, **kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr(slow_db.urllib.request, "urlopen", fake_urlopen)
    perf_values = itertools.cycle([1.0, 1.3])
    monkeypatch.setattr(slow_db.time, "perf_counter", lambda: next(perf_values))

    with instrumented_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 1"))

    assert len(error_calls) == 1

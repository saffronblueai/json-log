import json
import logging
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

import pytest

from jsonlog.formatter import JSONFormatter, SanitizedJSONFormatter


@pytest.fixture
def logger():
    logger = logging.getLogger()
    formatter = JSONFormatter()
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    return logger


def test_formatter_produces_json(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    log_message = "this is a warning"
    logger.warning(log_message)
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("level") == "WARNING"
    assert log.get("message") == log_message


def test_formatter_includes_extra_keys(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    extra = {"first_key": "first_value", "second_key": "second_value"}
    logger.warning("this is a warning", extra=extra)
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("first_key") == "first_value"
    assert log.get("second_key") == "second_value"


def test_formatter_handles_exceptions_in_messages(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    logger.warning(Exception("oh no"))
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("level") == "WARNING"
    assert log.get("message") == "oh no"


def test_formatter_handles_bad_json(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    logger.warning({"unserializable_thing_1": Exception()}, extra={"unserializable_thing_2": Exception()})
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("message") == "ERROR: could not serialize log message"
    assert "level" in log
    assert "timestamp" in log
    assert "name" in log
    assert "location" in log


def test_formatter_key_order(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    extra = {"first_key": "first_value", "second_key": "second_value"}
    logger.warning("this is a warning", extra=extra)
    log: Dict[str, Any] = json.loads(caplog.text)
    assert list(log.keys()) == [
        "level",
        "timestamp",
        "name",
        "location",
        "message",
        "first_key",
        "second_key",
    ]


def test_formatter_handles_exceptions(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    class CustomError(BaseException):
        pass

    try:
        raise CustomError("some exception")
    except CustomError:
        logger.exception("fatal error")

    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("level") == "ERROR"
    assert log.get("message") == "fatal error"
    assert log.get("exception_name") == "CustomError"
    assert log.get("exception", "").startswith("Traceback")
    assert 'raise CustomError("some exception")' in log.get("exception", "")


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "Authorization",
        "authorization",
        "Cookie",
        "cookie",
        "Set-Cookie",
        "set-cookie",
        "access_token",
        "refresh_token",
        "token",
    ],
)
def test_formatter_redacts_output(caplog: pytest.LogCaptureFixture, key: str):
    logger = logging.getLogger()
    formatter = SanitizedJSONFormatter()
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    extra = {
        key: "some value",
        "nested": {
            key: "some value",
        },
        "other_key": "other value",
        "other_nested": {
            "other_key": "other value",
        },
    }
    with caplog.at_level(logging.DEBUG):
        logger.debug("this is some debug", extra=extra)
        log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get(key) == "REDACTED"
    assert log.get("nested") == {key: "REDACTED"}
    assert log.get("other_key") == "other value"
    assert log.get("other_nested") == {"other_key": "other value"}


def test_formatter_stringifies_uuids_in_extra(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    test_uuid = uuid4()

    extra = {"uuid": test_uuid, "nested": {"key": test_uuid}}
    logger.warning("this is a warning", extra=extra)
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("uuid") == str(test_uuid)
    assert log.get("nested") == {"key": str(test_uuid)}


def test_formatter_stringifies_datetimes_in_extra(logger: logging.Logger, caplog: pytest.LogCaptureFixture):
    test_datetime = datetime.utcnow()

    extra = {"time": test_datetime, "nested": {"key": test_datetime}}
    logger.warning("this is a warning", extra=extra)
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("time") == str(test_datetime)
    assert log.get("nested") == {"key": str(test_datetime)}


def test_formatter_copies_nested(caplog: pytest.LogCaptureFixture):
    logger = logging.getLogger()
    formatter = SanitizedJSONFormatter()
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    extra: dict = {
        "password": "some value",
        "nested": {
            "password": "some value",
            "double_nested": {
                "password": "some value",
            },
        },
    }

    with caplog.at_level(logging.DEBUG):
        logger.debug("log", extra=extra)
        log: Dict[str, Any] = json.loads(caplog.text)

    assert log["nested"]["password"] == "REDACTED"
    assert extra["nested"]["password"] == "some value"

    assert log["nested"]["double_nested"]["password"] == "REDACTED"
    assert extra["nested"]["double_nested"]["password"] == "some value"

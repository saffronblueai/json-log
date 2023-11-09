import json
import logging
from collections import namedtuple
from typing import Any, Dict

import pytest

from jsonlog.utils import configure_logging

MockContext = namedtuple("MockContext", "aws_request_id function_name function_version")


def test_log_config(caplog: pytest.LogCaptureFixture):
    configure_logging(context=MockContext("some_req_id", "some_func_name", "some_func_version"))
    logger = logging.getLogger()
    logger.warning("this is a warning")
    log: Dict[str, Any] = json.loads(caplog.text)
    assert log.get("message") == "this is a warning"
    assert log.get("context") == {
        "request_id": "some_req_id",
        "function_name": "some_func_name",
        "function_version": "some_func_version",
    }

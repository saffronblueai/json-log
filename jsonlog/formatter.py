import dataclasses
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from uuid import UUID

RESERVED_LOG_ATTRS = (
    "name",
    "msg",
    "args",
    "level",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "asctime",
    "location",
    "timestamp",
)


@dataclasses.dataclass
class LogContext:
    request_id: str
    function_name: str
    function_version: str


# Stringify datetimes and UUIDs
def _json_default_serializer(obj):
    if isinstance(obj, (datetime, UUID)):
        return str(obj)
    raise Exception


class JSONFormatter(logging.Formatter):
    def __init__(self, context: Optional[LogContext] = None):
        self.context = context

    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {}
        try:
            formatted, extras, message = self._extract_log_components(log_record=record)
        except Exception:
            # just making a best effort at this point
            result_dict = {
                "level": data.get("level"),
                "timestamp": data.get("timestamp"),
                "name": data.get("name"),
                "location": data.get("location"),
                "message": "ERROR: could not serialize log message",
            }
            if data.get("context") or data.get("xray_trace_id"):
                result_dict.update(
                    {
                        "context": data.get("context"),
                        "xray_trace_id": data.get("xray_trace_id"),
                    }
                )
            return json.dumps(result_dict)

        data.update(formatted)
        data["message"] = message
        data.update(extras)
        data["exception"], data["exception_name"] = self._extract_log_exception(log_record=record)
        if self.context:
            data["context"] = dataclasses.asdict(self.context)
            data["xray_trace_id"] = self._get_latest_trace_id()
        data = self.filter_output({k: v for k, v in data.items() if v is not None})

        return json.dumps(data, default=_json_default_serializer)

    @property
    def log_format(self):
        return {
            "level": "%(levelname)s",
            "timestamp": "%(asctime)s",
            "name": "%(name)s",
            "location": "%(funcName)s:%(lineno)d",
        }

    @staticmethod
    def _get_latest_trace_id():
        xray_trace_id = os.getenv("_X_AMZN_TRACE_ID")
        return xray_trace_id.split(";")[0].replace("Root=", "") if xray_trace_id else None

    def _extract_log_exception(self, log_record: logging.LogRecord) -> Union[Tuple[str, str], Tuple[None, None]]:
        if log_record.exc_info and (exc_info := log_record.exc_info[0]):
            return self.formatException(log_record.exc_info), exc_info.__name__

        return None, None

    def _extract_log_components(
        self, log_record: logging.LogRecord
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Union[Dict[str, Any], str, bool, Iterable]]:
        record_dict = log_record.__dict__
        record_dict[
            "asctime"
        ] = f"{datetime.utcfromtimestamp(log_record.created):%Y-%m-%d %H:%M:%S}.{log_record.msecs:.3f}Z"

        extras = {k: v for k, v in record_dict.items() if k not in RESERVED_LOG_ATTRS}

        # Need to avoid passing values by reference, as we modify deeply nested
        # values when redacting sensitive values. Expect this to raise an exception
        # if any values are not json serializable. This is a faster alternative to
        # deepcopy
        extras = json.loads(json.dumps(extras, default=_json_default_serializer))

        formatted = {}

        for key, value in self.log_format.items():
            if value and key in RESERVED_LOG_ATTRS:
                formatted[key] = value % record_dict
            else:
                formatted[key] = value

        message = log_record.msg
        if isinstance(message, dict):
            message = message
        if isinstance(message, Exception):
            message = str(message)
        elif log_record.args:
            message = log_record.getMessage()  # format logger.info("foo %s", "bar")
        elif isinstance(message, str):
            try:
                message = json.loads(message)  # could be a JSON string
            except (json.decoder.JSONDecodeError, TypeError, ValueError):
                pass

        return formatted, extras, message

    def filter_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data


def _redact(json, redactkeys: List[str], case_insensitive: bool):
    if isinstance(json, list):
        for _, x in enumerate(json):
            if isinstance(x, dict) or isinstance(x, list):
                _redact(x, redactkeys, case_insensitive)

    if isinstance(json, dict):
        for k, v in json.items():
            if isinstance(v, dict) or isinstance(v, list):
                _redact(v, redactkeys, case_insensitive)
            elif not case_insensitive and k in redactkeys:
                json[k] = "REDACTED"
            elif case_insensitive and k.casefold() in redactkeys:
                json[k] = "REDACTED"
        return json


class SanitizedJSONFormatter(JSONFormatter):
    def __init__(
        self,
        context: Optional[LogContext] = None,
        redactkeys=[
            "password",
            "access_token",
            "refresh_token",
            "token",
            "set-cookie",
            "cookie",
            "authorization",
            "x-api-key",
        ],
        case_insensitive=True,
    ):
        super().__init__(context)
        self.redactkeys = redactkeys
        self.case_insensitive = case_insensitive

    def filter_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return _redact(data, self.redactkeys, self.case_insensitive)

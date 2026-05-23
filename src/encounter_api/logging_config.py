"""Application logging that keeps PHI out of every sink.

Two layers work together:

1. Convention. Callers log safe identifiers (request id, encounter id, actor),
   never patient data, and never interpolate PHI into a message string. The
   filter screens structured fields, not free-form message text.
2. Backstop. ``PHIRedactionFilter`` blanks any field whose name is a known PHI
   marker, at any nesting depth, before the record is formatted. So PHI passed
   as structured context cannot leak even if a log call is careless.

Records are emitted as line-delimited JSON, which is what log shippers expect
and what makes request-id correlation across services practical.
"""

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

REDACTED = "[REDACTED]"

# Field names treated as PHI wherever they appear in structured log context.
# Matched case-insensitively so both snake_case and camelCase keys are caught.
PHI_FIELD_NAMES = frozenset(
    {
        "patient_id",
        "patientid",
        "patient_name",
        "patientname",
        "patient",
        "name",
        "first_name",
        "last_name",
        "dob",
        "date_of_birth",
        "ssn",
        "mrn",
        "email",
        "phone",
        "address",
        "clinical_data",
        "clinicaldata",
    }
)

# Standard LogRecord attributes. Anything else on a record is caller-supplied
# context (the "extra" fields), which is what we serialize and screen.
_STANDARD_ATTRS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message", "asctime",
    }
)


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: (REDACTED if str(key).lower() in PHI_FIELD_NAMES else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


class PHIRedactionFilter(logging.Filter):
    """Redacts PHI-named fields from log records before they are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__):
            if key in _STANDARD_ATTRS:
                continue
            if key.lower() in PHI_FIELD_NAMES:
                record.__dict__[key] = REDACTED
            else:
                record.__dict__[key] = _redact(record.__dict__[key])

        if isinstance(record.args, Mapping):
            record.args = {
                key: (REDACTED if str(key).lower() in PHI_FIELD_NAMES else _redact(value))
                for key, value in record.args.items()
            }
        return True


class JsonFormatter(logging.Formatter):
    """Serializes a record to a single JSON line, including extra context.

    The exception type is recorded when present, but the traceback is not, so a
    stack carrying patient data in a local or message cannot reach the log. In
    production this pairs with an error tracker that scrubs PHI from full stacks.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter and PHI filter on the root logger.

    Idempotent: existing handlers are cleared first so repeated calls (tests,
    app reloads) do not stack duplicate output.
    """

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PHIRedactionFilter())
    root.addHandler(handler)

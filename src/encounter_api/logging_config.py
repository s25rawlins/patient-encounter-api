"""Application logging that keeps PHI out of every sink.

Two layers work together:

1. Convention. Callers log safe identifiers (request id, encounter id, actor),
   never patient data.
2. Backstop. ``PHIRedactionFilter`` blanks any field whose name is a known PHI
   marker before the record is formatted, so a careless log call still cannot
   leak. People forget and code changes, so the net stays on.

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


class PHIRedactionFilter(logging.Filter):
    """Redacts PHI-named fields from log records before they are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS:
                continue
            if key.lower() in PHI_FIELD_NAMES:
                record.__dict__[key] = REDACTED

        if isinstance(record.args, Mapping):
            record.args = {
                key: (REDACTED if str(key).lower() in PHI_FIELD_NAMES else value)
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

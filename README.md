# Patient Encounter API

A REST service for recording and retrieving patient clinical encounters, built with attention to
the PHI-handling and audit expectations of healthcare systems. Encounters carry session notes,
assessments, and clinical observations. The service validates every input at the API boundary,
keeps protected health information out of application logs, and records an audit trail of who
read or wrote which record and when.

This is a focused service, not a full platform. Storage is in-memory behind a repository
interface, and authentication is a mock JWT layer. The production path for both is described
under Production Considerations.

## Setup & Running

Requirements: Python 3.11+

Install (editable, with dev extras):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn encounter_api.main:app --reload
```

Interactive API docs are then served at http://127.0.0.1:8000/docs.

Run the tests:

```bash
pytest
```

## Design Decisions

_To be expanded during the build._

- Separation of concerns: API layer (routes), business logic (service), data access (repository).
- Validation strategy: where and how inputs are validated, and why at the boundary.
- Error handling: structured responses, no internal detail or stack traces leaked to clients.
- PHI redaction: how the logging filter keeps patient identifiers out of every log sink.
- Authentication: the mock JWT approach and what it stands in for.
- Extensibility: adding a new encounter type or field, and swapping the in-memory store.

## Testing Philosophy

_To be expanded during the build._

### What I tested
- Encounter roundtrip (create then retrieve).
- PHI redaction on error paths.
- Schema validation rejection.

### What I'd test with more time
1. _TBD_
2. _TBD_
3. _TBD_

### How I made this testable
- _TBD: dependency injection, repository interface, log capture approach._

## Production Considerations

_Stub. Filled last; this is where the real production hardening detail goes._

## Time Breakdown

_To be filled at the end._

# Patient Encounter API

A REST service for recording and retrieving patient clinical encounters, built
with the PHI-handling and audit expectations of healthcare systems in mind.
Encounters carry session notes, assessments, and clinical observations. The
service validates every input at the API boundary, keeps protected health
information out of application logs, and records an audit trail of who read or
wrote which record and when.

This is a focused service, not a full platform. Storage is in-memory behind a
repository interface, and authentication is a mock JWT layer. Both are
deliberately simple, with the production path described under
[Production Considerations](#production-considerations).

## Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/encounters` | Create an encounter, returns it with a generated id |
| `GET` | `/encounters/{encounterId}` | Fetch one encounter by id |
| `GET` | `/encounters` | List encounters, filtered by `patientId`, `providerId`, `from`, `to` |
| `GET` | `/audit/encounters` | Audit trail, filtered by `actorId`, `encounterId`, `from`, `to` |
| `GET` | `/health` | Liveness check |

All endpoints except `/health` require a bearer token.

## Setup & Running

Requirements: Python 3.11+.

Install in a virtual environment with the dev extras:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn encounter_api.main:app --reload
```

Interactive API docs are served at http://127.0.0.1:8000/docs.

The endpoints expect a signed token. Mint a development one with the helper used
by the test suite:

```bash
TOKEN=$(python -c "from encounter_api.auth import issue_token; print(issue_token('dr-okafor'))")

curl -s -X POST http://127.0.0.1:8000/encounters \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "patientId": "patient-2847",
        "providerId": "dr-okafor",
        "encounterDate": "2026-05-23T14:30:00Z",
        "encounterType": "follow_up",
        "clinicalData": {"note": "Patient reports improved sleep this week."}
      }'
```

Run the tests:

```bash
pytest
```

## Design Decisions

### Layered separation

Requests flow through three layers, each with one job:

- **Routes** (`routes/`) handle HTTP: parsing, status codes, response shaping.
- **Services** (`service.py`) hold the business rules: id generation,
  timestamps, audit writes.
- **Repositories** (`repository.py`) handle storage.

The service depends on repository *interfaces* (`typing.Protocol`), never on a
concrete store. The in-memory implementation backs this build; a Postgres-backed
one would satisfy the same interface and drop in without touching routes or
services. That boundary is also what makes the service unit-testable against a
fake store, with no web server in the loop.

### In-memory storage and its limits

Both stores are plain in-process collections guarded by a lock, because FastAPI
runs the sync handlers in a threadpool and concurrent requests would otherwise
interleave. They are unbounded and non-durable on purpose. The repository
interface is the seam where a real database takes over, and the production notes
cover persistence, retention, and partitioning.

### Validation at the boundary

Every request body is a Pydantic v2 model. The API speaks camelCase on the wire
while the Python stays snake_case, bridged by an alias generator, so neither side
has to compromise. Incoming payloads use `extra="forbid"`, so unknown or
misspelled fields are rejected rather than silently dropped. `clinicalData` is
intentionally open, since clinical content varies by encounter type.

### Error handling without disclosure

Exceptions are caught in one place and turned into a small, fixed-shape JSON
body. A validation failure returns 400 with the fields that failed and why, but
it never echoes the submitted values back, because a bad value could itself be
PHI. An unexpected error returns a generic 500. The real failure is logged
server-side under a request id (returned in the `X-Request-ID` header) for
correlation, with no stack trace sent to the client.

### PHI redaction in logs

Two layers keep patient data out of the logs:

1. **Convention.** Application code logs safe identifiers (request id, encounter
   id, actor), never patient fields, and never interpolates PHI into a message
   string.
2. **Backstop.** A `logging.Filter` blanks any field whose name is a known PHI
   marker, at any nesting depth, before the record is formatted, so PHI passed as
   structured context is scrubbed even when a log call is careless. The filter
   screens fields, not free-form message text, which is why the convention above
   pairs with it.

Logs are emitted as line-delimited JSON, which keeps `request_id` correlation
practical once these run across more than one process.

### Audit trail with PHI minimization

Every create and every read writes an audit record. Those records reference the
encounter by id and never store the patient id, so the audit log does not become
a second copy of patient data. If a reviewer needs the patient behind an access,
they resolve it through the encounter, which keeps PHI in one place.

### Authentication

Auth is a mock: a bearer token signed with a shared HS256 secret, verified on
every request, yielding a caller identity used for the audit trail. It exercises
the security boundary without standing up an identity provider. The production
path is below.

### What I did not build

In-memory storage, a single symmetric signing key, and no role-based access
control. Those are conscious omissions for a service of this scope, not
oversights. Each one is addressed in the production notes.

## Testing Philosophy

The goal is a few tests that fail loudly when something important regresses, not
a coverage number.

### What I tested

- **Encounter roundtrip.** POST then GET returns the same record, with the
  server-assigned id and metadata. This is the end-to-end contract: validation,
  id generation, storage, and serialization all have to agree.
- **PHI redaction.** The filter scrubs PHI-named fields directly, and a request
  that fails mid-flight leaks the patient id into neither the response nor the
  logs. This is the property that matters most for a healthcare service, so it
  is tested from both the unit and the request angle.
- **Schema validation.** Malformed input returns a structured 400 that names the
  failing fields without echoing submitted values or surfacing
  validation-library internals.

### What I'd test with more time, in priority order

1. Audit date-range and filter correctness (boundary inclusivity, combined
   filters).
2. Auth rejection paths: expired token, wrong issuer, wrong signature, missing
   claims.
3. List filtering across combinations of patient, provider, and date window.
4. Concurrency around the store, and the pagination contract once one exists.
5. A property-based check that any valid encounter survives a serialize and
   parse roundtrip.

### How I made this testable

- `create_app()` builds fresh repositories on each call, so every test is
  isolated with nothing to tear down.
- Dependencies resolve through FastAPI's injection, so a test can swap the
  service with `app.dependency_overrides` (the failure-path test uses this to
  force an error).
- Business logic lives in the service layer, behind repository interfaces, so it
  can be exercised without HTTP.
- Logging is configured so a test can attach its own handler and read exactly
  what would have been written.

## Production Considerations

What changes when this moves from a take-home-sized service to something handling
real PHI at scale.

### Storage and tenant isolation

Replace the in-memory repositories with Postgres behind the same interface. For
multi-tenant PHI, enable `FORCE ROW LEVEL SECURITY` on every tenant-scoped table
and set the tenant context per connection, so the database itself returns only
rows the current session may see. A misconfigured query then cannot leak across
tenants, because isolation lives at the storage layer rather than in application
code. Index the encounter table on `(patient_id, encounter_date)` for the common
filters, run reads through a pooled connection (PgBouncer in transaction mode),
and move list endpoints to keyset pagination so result sets stay bounded.

### Encryption

Encrypt PHI at rest with envelope encryption: a per-tenant data key that is
itself wrapped under a customer-managed key in a KMS. Decryption then requires
KMS access, which is logged and revocable, and rotating a tenant's key is a
re-wrap rather than a full re-encrypt. TLS everywhere in transit, terminated as
close to the workload as the threat model allows.

### Audit integrity and retention

The audit trail should be append-only and tamper-evident. A practical approach
is an HMAC-keyed hash chain: each row signs the hash of the previous row, with
the HMAC key held in KMS, so even a database administrator cannot rewrite history
without detection. HIPAA's documentation requirements push a six-year retention
floor; satisfy it with WORM storage, for example S3 Object Lock in compliance
mode, so retained records cannot be deleted or altered before their term.

### Authentication and authorization

Swap the HS256 mock for asymmetric tokens (ES384) issued by a real identity
provider and verified against a rotating JWKS endpoint, which fits SMART on FHIR
Backend Services for EMR integration. Add role-based access control so a clinician,
a billing user, and a compliance auditor see different slices, and record the
caller's role on each audit entry. Verify the audience (`aud`) claim too, so a
token minted for another service that shares the key is not accepted here.

### Observability

Keep the structured JSON logging, but route it through a centralized PHI-marker
configuration so redaction rules are defined once rather than per service. Pair
it with an error tracker that scrubs PHI from full stack traces, since the local
filter intentionally drops tracebacks to stay safe. Track request latency by
endpoint, error rate, audit-write failures, and token rejection rate, and alert
on the audit-write path specifically, because a silent audit failure is a
compliance gap, not just a bug.

### Scalability

The service is stateless once storage moves out of process, so it scales
horizontally behind a load balancer. The audit table grows without bound, so
partition it by time (monthly) and archive cold partitions to the WORM tier.
Add rate limiting at the edge and idempotency keys on `POST /encounters` so a
retried create does not produce duplicate records. Cap request body size at the
proxy and bound `clinicalData`, since an unbounded JSON blob is a
memory-exhaustion vector. The request-id middleware uses Starlette's
`BaseHTTPMiddleware`; a pure-ASGI middleware trims per-request overhead at scale.

## Time Breakdown

- Design and README skeleton: ~20 min
- Implementation (models, repositories, services, endpoints, auth, logging): ~70 min
- Tests: ~20 min
- README and production write-up: ~20 min

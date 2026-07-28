# Job Scheduler

A FastAPI service for creating background jobs, running them in Celery, and
tracking their status in PostgreSQL. Redis is used as the Celery broker.

Jobs are stored before they are queued. The worker reads the same database row,
runs the handler, and writes the result or error back to it.

## How it works

```text
client -> FastAPI -> PostgreSQL
                  -> Redis -> Celery worker -> PostgreSQL
```

1. The API validates the request and inserts a `pending` job.
2. The job is marked `queued` and `src.utils.tasks.process_job` is published.
3. The worker sets it to `running`, increments `attempts`, and calls the handler.
4. On success it saves `result` and sets `succeeded`.
5. On failure it saves `last_error` and either schedules a retry or marks the
   job `failed`.

The Celery task ID is the job UUID. If Redis is down during publishing, the job
is saved as `failed` and the API returns `503`.

## Run with Docker

```bash
docker compose up --build
```

| Service | URL |
| --- | --- |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

The API container applies Alembic migrations before it starts. The worker waits
for the API health check, so it starts after the schema is ready.

```bash
curl http://localhost:8000/health/ready
```

Copy `.env.example` to `.env` if you want to change ports or defaults.

## Examples

Create a job:

```bash
curl -X POST http://localhost:8000/jobs/create \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "add",
    "payload": {"a": 2, "b": 3},
    "max_retries": 3,
    "retry_backoff_seconds": 2
  }'
```

Response:

```json
{
  "message": "Job created successfully",
  "data": {
    "id": "d7b7e94b-7f39-49e3-9d5e-1f0f43b9d9e4",
    "job_type": "add",
    "status": "queued",
    "attempts": 0,
    "result": null,
    "last_error": null
  }
}
```

Get it later:

```bash
curl http://localhost:8000/jobs/<job-id>
```

A successful `add` job ends with:

```json
{
  "message": "Job fetched successfully",
  "data": {
    "status": "succeeded",
    "attempts": 1,
    "result": {"sum": 5, "job_id": "...", "attempt": 1}
  }
}
```

To watch retries, use the `flaky` demo job. It fails until attempt 2:

```bash
curl -X POST http://localhost:8000/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"job_type": "flaky", "payload": {"fail_until_attempt": 2}}'
```

To see a permanent failure:

```bash
curl -X POST http://localhost:8000/jobs/create \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "always_fail",
    "payload": {"message": "demo error"},
    "max_retries": 1,
    "retry_backoff_seconds": 1
  }'
```

Retry a failed job:

```bash
curl -X POST http://localhost:8000/jobs/<job-id>/retry
```

List jobs, filter by status, or delete a finished job:

```bash
curl "http://localhost:8000/jobs/?status=failed&page=1&page_size=10"
curl -X DELETE http://localhost:8000/jobs/<job-id>
```

Only `succeeded` and `failed` jobs can be deleted.

## API

Interactive docs are at `/docs` and `/redoc`. The full request/response
reference is in [docs/API.md](docs/API.md).

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/jobs/create` | Create and queue a job |
| `GET` | `/jobs/` | List jobs with `status`, `page`, `page_size` |
| `GET` | `/jobs/types` | List supported job types |
| `GET` | `/jobs/{job_id}` | Get one job |
| `POST` | `/jobs/{job_id}/retry` | Retry a failed job |
| `DELETE` | `/jobs/{job_id}` | Delete a finished job |
| `GET` | `/health/live` | Liveness |
| `GET` | `/health/ready` | PostgreSQL and Redis readiness |

Errors are wrapped by the app:

```json
{"message": "Request failed", "detail": "Job not found"}
```

Validation errors return `422` with `{"message": "Validation failed", "detail": [...]}`.

## Job types

| Type | Payload |
| --- | --- |
| `add` | `{"a": 2, "b": 3}` |
| `send_email` | `{"to": "a@example.com", "subject": "Hi", "simulate_seconds": 1}` |
| `flaky` | `{"fail_until_attempt": 2}` |
| `always_fail` | `{"message": "reason"}` |

`send_email` only simulates work. To add another job type, write a function in
[`src/utils/handlers.py`](src/utils/handlers.py), add it to `JOB_HANDLERS`, and
restart the API and worker.

## Retry behavior

A job is retried while `attempts <= max_retries`. The delay is:

```text
min(retry_backoff_seconds * 2^(attempt - 1), MAX_RETRY_BACKOFF_SECONDS)
```

With a base of 2 seconds and 3 retries:

| Failed attempt | Delay |
| --- | --- |
| 1 | 2s |
| 2 | 4s |
| 3 | 8s |
| 4 | no retry, job fails |

`max_retries: 3` means at most 4 executions. A manual retry resets `attempts`
to zero.

## Layout

```text
main.py
src/
|-- routes/
|   |-- jobs.py             # Job endpoints and DB logic
|   `-- health.py           # Health endpoints
|-- interfaces/jobs.py      # Pydantic request/response models
|-- models/jobs.py          # SQLAlchemy job model
`-- utils/
    |-- configs.py          # Settings
    |-- db.py               # Engine, session, get_db
    |-- celery.py           # Celery app
    |-- handlers.py         # Job functions and registry
    |-- queue.py            # Publish to Redis
    |-- retry.py            # Backoff calculation
    `-- tasks.py            # Celery task and retry lifecycle
```

Routes hold HTTP and database logic, `interfaces` holds Pydantic schemas,
`models` holds SQLAlchemy models, and `utils` holds configuration and helpers.

## Configuration

Settings are read from environment variables or `.env`.

| Variable | Default |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://jobqueue:jobqueue@localhost:5432/jobqueue` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `DEFAULT_MAX_RETRIES` | `3` |
| `DEFAULT_RETRY_BACKOFF_SECONDS` | `5` |
| `MAX_RETRY_BACKOFF_SECONDS` | `300` |
| `LOG_LEVEL` | `INFO` |

See [.env.example](.env.example) for the Compose port settings.

## Local development

Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env               # Windows: Copy-Item .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

Start the worker in another terminal:

```bash
celery -A src.utils.celery:celery_app worker --loglevel=INFO --pool=solo
```

Use `--pool=solo` on Windows. The default prefork pool works on Linux and macOS.

## Tests

The tests use SQLite and a fake broker, so PostgreSQL and Redis are not
required.

```bash
pytest -q
```

## Notes

- Delivery is at least once. A worker crash can cause a job to run twice, so
  real handlers should be safe to repeat.
- Celery results are disabled. Job status and output are always read from
  PostgreSQL.
- There is no authentication, scheduling, or cancellation.
- A message lost from Redis can leave a row in `queued`; a transactional outbox
  would be the next step for that failure case.

# API Reference

Base URL: `http://localhost:8000`

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

Successful responses use a `message` and `data` envelope. Errors use `message`
and `detail`.

## Job object

```json
{
  "id": "d7b7e94b-7f39-49e3-9d5e-1f0f43b9d9e4",
  "job_type": "add",
  "payload": {"a": 2, "b": 3},
  "status": "queued",
  "attempts": 0,
  "max_retries": 3,
  "retry_backoff_seconds": 2,
  "result": null,
  "last_error": null,
  "created_at": "2026-11-26T17:00:00Z",
  "updated_at": "2026-11-26T17:00:00Z",
  "started_at": null,
  "finished_at": null,
  "next_retry_at": null
}
```

| Field | Description |
| --- | --- |
| `id` | Job UUID, also used as the Celery task ID |
| `job_type` | Registered handler name |
| `payload` | Input passed to the handler |
| `status` | Current state |
| `attempts` | Number of executions started |
| `max_retries` | Retries allowed after the first attempt |
| `retry_backoff_seconds` | Base delay for exponential backoff |
| `result` | Handler output after success |
| `last_error` | Most recent failure message |
| `created_at` | Creation time |
| `updated_at` | Last update time |
| `started_at` | First attempt start time |
| `finished_at` | Time the job reached a terminal state |
| `next_retry_at` | Scheduled retry time while status is `retrying` |

### Status values

| Status | Meaning |
| --- | --- |
| `pending` | Saved but not published yet |
| `queued` | Published to Redis |
| `running` | Being executed |
| `retrying` | Failed, with another attempt scheduled |
| `succeeded` | Completed successfully |
| `failed` | Enqueue failed or retries were exhausted |

## Create a job

`POST /jobs/create` returns `202 Accepted`.

```bash
curl -X POST http://localhost:8000/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"job_type":"add","payload":{"a":2,"b":3}}'
```

Request body:

| Field | Required | Default | Notes |
| --- | --- | --- | --- |
| `job_type` | yes | - | Must be in the handler registry |
| `payload` | no | `{}` | JSON object |
| `max_retries` | no | `3` | 0 to 10 |
| `retry_backoff_seconds` | no | `5` | 1 to `MAX_RETRY_BACKOFF_SECONDS` |

Response:

```json
{
  "message": "Job created successfully",
  "data": {
    "id": "d7b7e94b-7f39-49e3-9d5e-1f0f43b9d9e4",
    "job_type": "add",
    "status": "queued"
  }
}
```

The returned job is usually `queued`, but can already be `running` or
`succeeded` if the worker is fast.

Unknown job types return `400`. If Redis rejects the publish, the job is saved
as `failed` and the API returns `503`:

```json
{
  "message": "Request failed",
  "detail": {
    "message": "Job was saved but Redis did not accept it",
    "job_id": "d7b7e94b-7f39-49e3-9d5e-1f0f43b9d9e4"
  }
}
```

## List jobs

`GET /jobs/`

| Query | Default | Notes |
| --- | --- | --- |
| `status` | none | Filter by status |
| `page` | `1` | Starts at 1 |
| `page_size` | `20` | 1 to 100 |

Response:

```json
{
  "message": "Jobs fetched successfully",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20,
    "pages": 0
  }
}
```

## Get a job

`GET /jobs/{job_id}`

```json
{
  "message": "Job fetched successfully",
  "data": {}
}
```

Returns `404` with `{"message": "Request failed", "detail": "Job not found"}`
when the job does not exist.

## List job types

`GET /jobs/types`

```json
{
  "message": "Job types fetched successfully",
  "data": [
    {
      "name": "add",
      "description": "Add two numbers. Payload: {\"a\": number, \"b\": number}."
    }
  ]
}
```

## Retry a job

`POST /jobs/{job_id}/retry` returns `202 Accepted`.

Only a `failed` job can be retried. This resets `attempts`, `result`,
`last_error`, and the timestamps, then publishes the job again.

| Case | Response |
| --- | --- |
| Job failed | `202` with the updated job |
| Job not failed | `409` |
| Job not found | `404` |
| Redis unavailable | `503`; the job stays failed |

## Delete a job

`DELETE /jobs/{job_id}` returns `200 OK`.

```json
{"message": "Job deleted successfully"}
```

Only `succeeded` or `failed` jobs can be deleted. Active jobs return `409`.

## Health

`GET /health/live` returns `200` while the API process is running.

`GET /health/ready` checks PostgreSQL and Redis:

```json
{
  "message": "Service is healthy",
  "data": {"database": "ok", "redis": "ok"}
}
```

It returns `503` when either check fails.

## Errors

Application errors:

```json
{"message": "Request failed", "detail": "Only failed jobs can be retried"}
```

Validation errors use `422`:

```json
{
  "message": "Validation failed",
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "max_retries"],
      "msg": "Input should be greater than or equal to 0",
      "input": -1
    }
  ]
}
```

Unhandled errors return `500` with `{"message": "Internal server error", "detail": "Something went wrong"}`.

## Handler payloads

| Type | Payload | Result |
| --- | --- | --- |
| `add` | `{"a": 2, "b": 3}` | `{"sum": 5, ...}` |
| `send_email` | `{"to": "a@example.com", "subject": "Hi", "simulate_seconds": 1}` | Simulated email metadata |
| `flaky` | `{"fail_until_attempt": 2}` | Succeeds on the chosen attempt |
| `always_fail` | `{"message": "reason"}` | Raises `RuntimeError` |

`send_email` does not send a real email. The delay is capped at 10 seconds.

## Delivery

Celery can deliver a task more than once if a worker dies before acknowledging
it. Jobs are not exactly-once. Handlers with external side effects should be
idempotent.

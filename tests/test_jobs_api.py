import uuid

from sqlalchemy import select

from src.models.jobs import Job, JobStatus, utc_now


def test_root_and_openapi(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["message"] == "Job Scheduler API"

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/jobs/create" in openapi.json()["paths"]


def test_create_job_queues_it(client, queue_calls):
    response = client.post(
        "/jobs/create",
        json={
            "job_type": "add",
            "payload": {"a": 2, "b": 3},
            "max_retries": 2,
            "retry_backoff_seconds": 2,
        },
    )

    assert response.status_code == 202
    body = response.json()
    job = body["data"]
    assert body["message"] == "Job created successfully"
    assert job["status"] == "queued"
    assert job["attempts"] == 0
    assert job["max_retries"] == 2
    assert job["retry_backoff_seconds"] == 2
    assert job["last_error"] is None
    assert len(queue_calls) == 1
    assert queue_calls[0]["args"] == [job["id"]]
    assert queue_calls[0]["task_id"] == job["id"]

    job_id = uuid.UUID(job["id"])
    detail = client.get(f"/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == job["id"]


def test_rejects_unknown_job_type(client):
    response = client.post(
        "/jobs/create",
        json={"job_type": "does_not_exist", "payload": {}},
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Request failed"


def test_rejects_invalid_retry_settings(client):
    response = client.post(
        "/jobs/create",
        json={
            "job_type": "add",
            "payload": {"a": 1, "b": 2},
            "max_retries": 99,
        },
    )
    assert response.status_code == 422
    assert response.json()["message"] == "Validation failed"


def test_get_unknown_job_returns_404(client):
    response = client.get(f"/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_list_filter_and_pagination(client, queue_calls):
    for number in range(3):
        response = client.post(
            "/jobs/create",
            json={
                "job_type": "add",
                "payload": {"a": number, "b": 1},
            },
        )
        assert response.status_code == 202

    response = client.get("/jobs/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2

    queued = client.get("/jobs/?status=queued")
    assert queued.status_code == 200
    assert queued.json()["data"]["total"] == 3

    failed = client.get("/jobs/?status=failed")
    assert failed.status_code == 200
    assert failed.json()["data"]["total"] == 0


def test_retry_is_rejected_while_job_is_queued(client, queue_calls):
    created = client.post(
        "/jobs/create",
        json={"job_type": "add", "payload": {"a": 1, "b": 1}},
    ).json()["data"]

    response = client.post(f"/jobs/{created['id']}/retry")
    assert response.status_code == 409
    assert response.json()["detail"] == "Only failed jobs can be retried"


def test_delete_is_rejected_for_active_job(client, queue_calls):
    created = client.post(
        "/jobs/create",
        json={"job_type": "add", "payload": {"a": 1, "b": 1}},
    ).json()["data"]

    response = client.delete(f"/jobs/{created['id']}")
    assert response.status_code == 409


def test_delete_finished_job(client, queue_calls, db_session):
    created = client.post(
        "/jobs/create",
        json={"job_type": "add", "payload": {"a": 1, "b": 1}},
    ).json()["data"]

    job = db_session.scalar(
        select(Job).where(Job.id == uuid.UUID(created["id"]))
    )
    job.status = JobStatus.SUCCEEDED
    job.finished_at = utc_now()
    db_session.commit()

    response = client.delete(f"/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json()["message"] == "Job deleted successfully"
    assert client.get(f"/jobs/{created['id']}").status_code == 404


def test_enqueue_failure_marks_job_failed(
    client, monkeypatch, db_session
):
    from src.utils.celery import celery_app

    def broken_broker(*args, **kwargs):
        raise ConnectionError("redis is down")

    monkeypatch.setattr(celery_app, "send_task", broken_broker)

    response = client.post(
        "/jobs/create",
        json={"job_type": "add", "payload": {"a": 1, "b": 1}},
    )
    assert response.status_code == 503
    job_id = response.json()["detail"]["job_id"]

    stored = db_session.scalar(
        select(Job).where(Job.id == uuid.UUID(job_id))
    )
    assert stored is not None
    assert stored.status == JobStatus.FAILED
    assert "Could not enqueue job" in stored.last_error


def test_manual_retry_of_failed_job(client, monkeypatch, db_session):
    from src.utils.celery import celery_app

    def broken_broker(*args, **kwargs):
        raise ConnectionError("redis is down")

    monkeypatch.setattr(celery_app, "send_task", broken_broker)
    created = client.post(
        "/jobs/create",
        json={"job_type": "add", "payload": {"a": 1, "b": 1}},
    )
    assert created.status_code == 503
    job_id = created.json()["detail"]["job_id"]

    queued_calls = []

    def working_broker(name, args=None, task_id=None, **kwargs):
        queued_calls.append(task_id)

    monkeypatch.setattr(celery_app, "send_task", working_broker)

    retried = client.post(f"/jobs/{job_id}/retry")
    assert retried.status_code == 202
    body = retried.json()
    job = body["data"]
    assert job["status"] == "queued"
    assert job["attempts"] == 0
    assert job["last_error"] is None
    assert job["result"] is None
    assert queued_calls == [job_id]

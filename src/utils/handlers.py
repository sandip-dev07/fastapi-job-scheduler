from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobContext:
    job_id: uuid.UUID
    attempt: int


JobHandler = Callable[[dict[str, Any], JobContext], dict[str, Any]]


@dataclass(frozen=True)
class JobDefinition:
    description: str
    handler: JobHandler


def _number(payload: dict[str, Any], key: str) -> int | float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"payload.{key} must be a number")
    return value


def add_numbers(payload: dict[str, Any], context: JobContext) -> dict[str, Any]:
    a = _number(payload, "a")
    b = _number(payload, "b")
    return {
        "sum": a + b,
        "job_id": str(context.job_id),
        "attempt": context.attempt,
    }


def send_email(payload: dict[str, Any], context: JobContext) -> dict[str, Any]:
    """Simulated email. No real message is sent."""

    to = payload.get("to")
    if not isinstance(to, str) or "@" not in to:
        raise ValueError("payload.to must be a valid email address")

    subject = payload.get("subject", "(no subject)")
    if not isinstance(subject, str):
        raise ValueError("payload.subject must be a string")

    delay = payload.get("simulate_seconds", 1)
    if isinstance(delay, bool) or not isinstance(delay, (int, float)):
        raise ValueError("payload.simulate_seconds must be a number")
    if not 0 <= delay <= 10:
        raise ValueError("payload.simulate_seconds must be between 0 and 10")

    time.sleep(delay)

    return {
        "message": "Email simulated successfully",
        "message_id": f"email-{context.job_id.hex[:8]}-{context.attempt}",
        "to": to,
        "subject": subject,
    }


def flaky_job(payload: dict[str, Any], context: JobContext) -> dict[str, Any]:
    fail_until_attempt = payload.get("fail_until_attempt", 2)
    if (
        isinstance(fail_until_attempt, bool)
        or not isinstance(fail_until_attempt, int)
        or not 1 <= fail_until_attempt <= 10
    ):
        raise ValueError(
            "payload.fail_until_attempt must be an integer between 1 and 10"
        )

    if context.attempt < fail_until_attempt:
        raise RuntimeError(
            f"Simulated failure on attempt {context.attempt}; "
            f"succeeding on attempt {fail_until_attempt}"
        )

    return {
        "message": "Flaky job recovered",
        "attempt": context.attempt,
        "job_id": str(context.job_id),
    }


def always_fail(payload: dict[str, Any], context: JobContext) -> dict[str, Any]:
    message = payload.get("message", "This job always fails")
    if not isinstance(message, str):
        raise ValueError("payload.message must be a string")
    raise RuntimeError(message)


JOB_HANDLERS: dict[str, JobDefinition] = {
    "add": JobDefinition(
        description="Add two numbers. Payload: {\"a\": number, \"b\": number}.",
        handler=add_numbers,
    ),
    "send_email": JobDefinition(
        description=(
            "Simulate sending an email. Payload: "
            "{\"to\": string, \"subject\": string, \"simulate_seconds\": number}."
        ),
        handler=send_email,
    ),
    "flaky": JobDefinition(
        description=(
            "Fails until a given attempt, then succeeds. Payload: "
            "{\"fail_until_attempt\": integer}."
        ),
        handler=flaky_job,
    ),
    "always_fail": JobDefinition(
        description="Always fails. Payload: {\"message\": string}.",
        handler=always_fail,
    ),
}


def get_handler(job_type: str) -> JobHandler:
    definition = JOB_HANDLERS.get(job_type)
    if definition is None:
        supported = ", ".join(sorted(JOB_HANDLERS))
        raise ValueError(
            f"Unsupported job type '{job_type}'. Supported types: {supported}"
        )
    return definition.handler

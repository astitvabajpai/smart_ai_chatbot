import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from app.core.config import get_settings


class JobManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._executor = ThreadPoolExecutor(max_workers=max(2, self.settings.api_workers))
        self._lock = threading.Lock()
        self._state_path = Path(self.settings.job_state_path)
        if not self._state_path.exists():
            self._state_path.write_text("{}", encoding="utf-8")

    def submit(self, user_id: str, job_type: str, fn: Callable[[], dict]) -> str:
        job_id = str(uuid.uuid4())
        self._update_state(
            job_id,
            {
                "job_id": job_id,
                "user_id": user_id,
                "job_type": job_type,
                "status": "queued",
                "result": {},
                "error": None,
                "created_at": datetime.now(tz=UTC).isoformat(),
                "updated_at": datetime.now(tz=UTC).isoformat(),
            },
        )

        def run_job() -> None:
            self._patch_state(job_id, status="running", updated_at=datetime.now(tz=UTC).isoformat())
            try:
                result = fn()
                self._patch_state(
                    job_id,
                    status="completed",
                    result=result,
                    updated_at=datetime.now(tz=UTC).isoformat(),
                )
            except Exception as exc:  # noqa: BLE001
                self._patch_state(
                    job_id,
                    status="failed",
                    error=str(exc),
                    updated_at=datetime.now(tz=UTC).isoformat(),
                )

        self._executor.submit(run_job)
        return job_id

    def get(self, job_id: str) -> dict | None:
        state = self._read_state()
        return state.get(job_id)

    def list_for_user(self, user_id: str) -> list[dict]:
        state = self._read_state()
        jobs = [job for job in state.values() if job.get("user_id") == user_id]
        return sorted(jobs, key=lambda item: item["created_at"], reverse=True)

    def _read_state(self) -> dict:
        with self._lock:
            return json.loads(self._state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict) -> None:
        with self._lock:
            self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _update_state(self, job_id: str, record: dict) -> None:
        state = self._read_state()
        state[job_id] = record
        self._write_state(state)

    def _patch_state(self, job_id: str, **kwargs: dict) -> None:
        state = self._read_state()
        if job_id not in state:
            return
        state[job_id].update(kwargs)
        self._write_state(state)

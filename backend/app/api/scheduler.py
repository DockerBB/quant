"""API routes for task scheduler management."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter, HTTPException

from ..models.schemas import ScheduledTask
from ..scheduler.manager import scheduler_manager

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/tasks", response_model=List[ScheduledTask])
def list_tasks():
    jobs = scheduler_manager.scheduler.get_jobs()
    result = []
    for job in jobs:
        trigger = job.trigger
        cron_str = None
        if isinstance(trigger, CronTrigger):
            cron_str = (
                f"{trigger.fields[4]} {trigger.fields[3]} {trigger.fields[2]} "
                f"{trigger.fields[1]} {trigger.fields[0]}"
            )
        result.append(ScheduledTask(
            id=job.id,
            name=job.name,
            task_type=job.kwargs.get("task_type", "unknown"),
            cron_expr=cron_str,
            is_active=job.next_run_time is not None if hasattr(job, 'next_run_time') else True,
            last_run=datetime.now().isoformat(),
            next_run=job.next_run_time.isoformat() if job.next_run_time else None,
            config=job.kwargs.get("config", {}),
        ))
    return result


@router.post("/tasks/{task_id}/run-now")
def run_task_now(task_id: str):
    try:
        job = scheduler_manager.scheduler.get_job(task_id)
        if job is None:
            raise HTTPException(404, f"Task {task_id} not found")
        scheduler_manager.scheduler.add_job(
            job.func,
            trigger=DateTrigger(run_date=datetime.now() + timedelta(seconds=1)),
            args=job.args,
            kwargs=job.kwargs,
            id=f"run_now_{task_id}_{int(datetime.now().timestamp())}",
            name=f"{job.name} (run-once)",
        )
        return {"status": "ok", "task_id": task_id, "note": "Job submitted to scheduler"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: str):
    job = scheduler_manager.scheduler.get_job(task_id)
    if job is None:
        raise HTTPException(404, f"Task {task_id} not found")
    try:
        if job.next_run_time:
            scheduler_manager.scheduler.pause_job(task_id)
            return {"status": "paused", "task_id": task_id}
        scheduler_manager.scheduler.resume_job(task_id)
        return {"status": "resumed", "task_id": task_id}
    except Exception as e:
        raise HTTPException(500, str(e))

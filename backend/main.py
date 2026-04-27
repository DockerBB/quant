"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import data, factors, scheduler, signals, strategies
from app.core.config import settings
from app.core.database import init_metadata_tables
from app.scheduler.manager import scheduler_manager
from app.scheduler.tasks import daily_data_refresh, daily_strategy_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_metadata_tables()
    scheduler_manager.start()

    # Register default daily jobs
    scheduler_manager.add_job(
        daily_data_refresh,
        CronTrigger(
            hour=settings.DATA_REFRESH_HOUR,
            minute=settings.DATA_REFRESH_MINUTE,
            day_of_week="mon-fri",
        ),
        job_id="daily_data_refresh",
        name="每日数据刷新",
        task_type="data_refresh",
    )
    scheduler_manager.add_job(
        daily_strategy_run,
        CronTrigger(hour=17, minute=0, day_of_week="mon-fri"),
        job_id="daily_strategy_run",
        name="每日策略运行",
        task_type="strategy_run",
    )

    yield

    # Shutdown
    scheduler_manager.shutdown()


app = FastAPI(
    title="Quant Strategy System",
    description="A股量化选股与信号生成系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(factors.router)
app.include_router(strategies.router)
app.include_router(signals.router)
app.include_router(scheduler.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)

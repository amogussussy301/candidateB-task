import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.staticfiles import StaticFiles

from app.database import connect, initialize_database
from app.reporting import build_report
from app.schemas import Report

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(
    data_dir: Path | None = None,
    db_path: Path | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    source_dir = data_dir or PROJECT_ROOT / "data"
    database_path = db_path or PROJECT_ROOT / "backend" / "report.db"
    frontend_dir = static_dir or PROJECT_ROOT / "frontend" / "dist"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(database_path, source_dir)
        yield

    app = FastAPI(title="Авансы по договорам", lifespan=lifespan)

    def get_connection() -> Iterator[sqlite3.Connection]:
        connection = connect(database_path)
        try:
            yield connection
        finally:
            connection.close()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/report", response_model=Report)
    def report(
        report_date: Annotated[date, Query(description="Дата отчёта, ГГГГ-ММ-ДД")],
        connection: Annotated[sqlite3.Connection, Depends(get_connection)],
    ) -> Report:
        return build_report(connection, report_date)

    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()

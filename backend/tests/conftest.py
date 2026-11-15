import sqlite3
from collections.abc import Iterator
from pathlib import Path
from shutil import copytree

import pytest
from fastapi.testclient import TestClient

from app.database import connect, initialize_database
from app.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATA = PROJECT_ROOT / "data"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    destination = tmp_path / "data"
    copytree(SOURCE_DATA, destination)
    return destination


@pytest.fixture
def db_path(data_dir: Path, tmp_path: Path) -> Path:
    path = tmp_path / "report.db"
    initialize_database(path, data_dir)
    return path


@pytest.fixture
def connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    database = connect(db_path)
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def client(data_dir: Path, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        data_dir=data_dir,
        db_path=tmp_path / "api.db",
        static_dir=tmp_path / "no-static",
    )
    with TestClient(app) as test_client:
        yield test_client

import csv
import sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal, overload

CONTRACT_FIELDS = ("contract_id", "contractor", "amount", "signed_at")
WORK_FIELDS = (
    "work_id",
    "contract_id",
    "title",
    "price",
    "status",
    "completed_at",
    "cancelled_at",
)
PAYMENT_FIELDS = (
    "payment_id",
    "contract_id",
    "work_id",
    "purpose",
    "amount",
    "status",
    "created_at",
    "paid_at",
    "refunded_at",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT PRIMARY KEY,
    contractor TEXT NOT NULL,
    amount_kopecks INTEGER NOT NULL CHECK (amount_kopecks >= 0),
    signed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS works (
    work_id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES contracts(contract_id),
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    price_kopecks INTEGER NOT NULL CHECK (price_kopecks >= 0),
    status TEXT NOT NULL CHECK (status IN ('planned', 'done', 'cancelled')),
    completed_at TEXT,
    cancelled_at TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES contracts(contract_id),
    work_id TEXT REFERENCES works(work_id),
    position INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    amount_kopecks INTEGER NOT NULL CHECK (amount_kopecks >= 0),
    status TEXT NOT NULL CHECK (status IN ('paid', 'queued', 'refunded')),
    created_at TEXT NOT NULL,
    paid_at TEXT,
    refunded_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_works_contract ON works(contract_id, position);
CREATE INDEX IF NOT EXISTS idx_payments_contract ON payments(contract_id, position);
"""


class DataError(ValueError):
    """Raised when source CSV data is inconsistent."""


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path, data_dir: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as connection:
        connection.executescript(SCHEMA)
        load_data(connection, data_dir)


def load_data(connection: sqlite3.Connection, data_dir: Path) -> None:
    contracts = _read_contracts(data_dir / "contracts.csv")
    works = _read_works(data_dir / "works.csv", contracts)
    payments = _read_payments(data_dir / "payments.csv", contracts, works)

    with connection:
        connection.execute("DELETE FROM payments")
        connection.execute("DELETE FROM works")
        connection.execute("DELETE FROM contracts")
        connection.executemany(
            """
            INSERT INTO contracts (contract_id, contractor, amount_kopecks, signed_at)
            VALUES (:contract_id, :contractor, :amount_kopecks, :signed_at)
            """,
            contracts.values(),
        )
        connection.executemany(
            """
            INSERT INTO works (
                work_id, contract_id, position, title, price_kopecks,
                status, completed_at, cancelled_at
            ) VALUES (
                :work_id, :contract_id, :position, :title, :price_kopecks,
                :status, :completed_at, :cancelled_at
            )
            """,
            works.values(),
        )
        connection.executemany(
            """
            INSERT INTO payments (
                payment_id, contract_id, work_id, position, purpose,
                amount_kopecks, status, created_at, paid_at, refunded_at
            ) VALUES (
                :payment_id, :contract_id, :work_id, :position, :purpose,
                :amount_kopecks, :status, :created_at, :paid_at, :refunded_at
            )
            """,
            payments,
        )


def _read_rows(
    path: Path, required_fields: tuple[str, ...]
) -> list[tuple[int, dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = tuple(reader.fieldnames or ())
        missing = set(required_fields) - set(fieldnames)
        if missing:
            raise DataError(
                f"{path.name}: отсутствуют колонки: {', '.join(sorted(missing))}"
            )

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise DataError(f"{path.name}:{line_number}: лишние значения в строке")
            rows.append(
                (
                    line_number,
                    {
                        field: (row.get(field) or "").strip()
                        for field in required_fields
                    },
                )
            )
        return rows


def _read_contracts(path: Path) -> dict[str, dict[str, str | int]]:
    contracts: dict[str, dict[str, str | int]] = {}
    for line_number, row in _read_rows(path, CONTRACT_FIELDS):
        context = f"{path.name}:{line_number}"
        contract_id = _required(row["contract_id"], "contract_id", context)
        if contract_id in contracts:
            raise DataError(f"{context}: повторяющийся договор {contract_id}")
        contracts[contract_id] = {
            "contract_id": contract_id,
            "contractor": _required(row["contractor"], "contractor", context),
            "amount_kopecks": _money_to_kopecks(row["amount"], context),
            "signed_at": _date(row["signed_at"], "signed_at", context, required=True),
        }
    return contracts


def _read_works(
    path: Path, contracts: dict[str, dict[str, str | int]]
) -> dict[str, dict[str, str | int | None]]:
    works: dict[str, dict[str, str | int | None]] = {}
    for position, (line_number, row) in enumerate(_read_rows(path, WORK_FIELDS)):
        context = f"{path.name}:{line_number}"
        work_id = _required(row["work_id"], "work_id", context)
        contract_id = _required(row["contract_id"], "contract_id", context)
        if work_id in works:
            raise DataError(f"{context}: повторяющаяся работа {work_id}")
        if contract_id not in contracts:
            raise DataError(f"{context}: неизвестный договор {contract_id}")

        status = row["status"]
        if status not in {"planned", "done", "cancelled"}:
            raise DataError(f"{context}: неизвестный статус работы {status}")
        completed_at = _date(row["completed_at"], "completed_at", context)
        cancelled_at = _date(row["cancelled_at"], "cancelled_at", context)
        _validate_work_dates(status, completed_at, cancelled_at, context)

        works[work_id] = {
            "work_id": work_id,
            "contract_id": contract_id,
            "position": position,
            "title": _required(row["title"], "title", context),
            "price_kopecks": _money_to_kopecks(row["price"], context),
            "status": status,
            "completed_at": completed_at,
            "cancelled_at": cancelled_at,
        }
    return works


def _read_payments(
    path: Path,
    contracts: dict[str, dict[str, str | int]],
    works: dict[str, dict[str, str | int | None]],
) -> list[dict[str, str | int | None]]:
    payments: list[dict[str, str | int | None]] = []
    payment_ids: set[str] = set()
    for position, (line_number, row) in enumerate(_read_rows(path, PAYMENT_FIELDS)):
        context = f"{path.name}:{line_number}"
        payment_id = _required(row["payment_id"], "payment_id", context)
        contract_id = _required(row["contract_id"], "contract_id", context)
        work_id = row["work_id"] or None
        if payment_id in payment_ids:
            raise DataError(f"{context}: повторяющийся платёж {payment_id}")
        if contract_id not in contracts:
            raise DataError(f"{context}: неизвестный договор {contract_id}")
        if work_id is not None:
            if work_id not in works:
                raise DataError(f"{context}: неизвестная работа {work_id}")
            if works[work_id]["contract_id"] != contract_id:
                raise DataError(
                    f"{context}: работа {work_id} относится к другому договору"
                )

        status = row["status"]
        if status not in {"paid", "queued", "refunded"}:
            raise DataError(f"{context}: неизвестный статус платежа {status}")
        paid_at = _date(row["paid_at"], "paid_at", context)
        refunded_at = _date(row["refunded_at"], "refunded_at", context)
        _validate_payment_dates(status, paid_at, refunded_at, context)

        payment_ids.add(payment_id)
        payments.append(
            {
                "payment_id": payment_id,
                "contract_id": contract_id,
                "work_id": work_id,
                "position": position,
                "purpose": row["purpose"],
                "amount_kopecks": _money_to_kopecks(row["amount"], context),
                "status": status,
                "created_at": _date(
                    row["created_at"], "created_at", context, required=True
                ),
                "paid_at": paid_at,
                "refunded_at": refunded_at,
            }
        )
    return payments


def _required(value: str, field: str, context: str) -> str:
    if not value:
        raise DataError(f"{context}: пустое поле {field}")
    return value


def _money_to_kopecks(value: str, context: str) -> int:
    try:
        amount = Decimal(_required(value, "amount/price", context))
    except InvalidOperation as error:
        raise DataError(f"{context}: некорректная сумма {value!r}") from error
    if not amount.is_finite() or amount < 0:
        raise DataError(f"{context}: сумма должна быть конечной и неотрицательной")
    kopecks = amount * 100
    if kopecks != kopecks.to_integral_value():
        raise DataError(f"{context}: сумма не должна содержать доли копейки")
    return int(kopecks)


@overload
def _date(value: str, field: str, context: str, required: Literal[True]) -> str: ...


@overload
def _date(
    value: str, field: str, context: str, required: Literal[False] = False
) -> str | None: ...


def _date(value: str, field: str, context: str, required: bool = False) -> str | None:
    if not value:
        if required:
            raise DataError(f"{context}: пустое поле {field}")
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise DataError(f"{context}: некорректная дата {value!r}") from error


def _validate_work_dates(
    status: str, completed_at: str | None, cancelled_at: str | None, context: str
) -> None:
    expected = {"done": completed_at, "cancelled": cancelled_at, "planned": None}
    if status == "done" and (completed_at is None or cancelled_at is not None):
        raise DataError(f"{context}: для done нужна только дата completed_at")
    if status == "cancelled" and (cancelled_at is None or completed_at is not None):
        raise DataError(f"{context}: для cancelled нужна только дата cancelled_at")
    if status == "planned" and (completed_at is not None or cancelled_at is not None):
        raise DataError(
            f"{context}: для planned даты завершения и отмены должны быть пустыми"
        )
    if status not in expected:
        raise DataError(f"{context}: неизвестный статус работы {status}")


def _validate_payment_dates(
    status: str, paid_at: str | None, refunded_at: str | None, context: str
) -> None:
    if status == "queued" and (paid_at is not None or refunded_at is not None):
        raise DataError(f"{context}: у queued не должно быть дат оплаты и возврата")
    if status == "paid" and (paid_at is None or refunded_at is not None):
        raise DataError(f"{context}: для paid нужна только дата paid_at")
    if status == "refunded":
        if paid_at is None or refunded_at is None:
            raise DataError(f"{context}: для refunded нужны даты paid_at и refunded_at")
        if refunded_at < paid_at:
            raise DataError(f"{context}: возврат не может быть раньше оплаты")

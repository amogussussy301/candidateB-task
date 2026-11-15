import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.database import DataError, connect, initialize_database, load_data
from app.reporting import build_report
from app.schemas import ContractReport, Report, WorkReport


def _contract(report: Report, contract_id: str) -> ContractReport:
    return next(
        contract for contract in report.contracts if contract.contract_id == contract_id
    )


def _work(report: Report, work_id: str) -> WorkReport:
    return next(
        work
        for contract in report.contracts
        for work in contract.works
        if work.work_id == work_id
    )


def test_reference_report_on_2026_11_10(connection: sqlite3.Connection) -> None:
    report = build_report(connection, date(2026, 11, 10))
    first, second = report.contracts

    assert (
        first.contract_amount,
        first.active_works_amount,
        first.paid,
        first.remaining,
        first.unallocated,
    ) == tuple(
        map(Decimal, ("600000.00", "500000.00", "315000.00", "185000.00", "0.00"))
    )
    assert (
        second.contract_amount,
        second.active_works_amount,
        second.paid,
        second.remaining,
        second.unallocated,
    ) == tuple(map(Decimal, ("90000.00", "90000.00", "75000.00", "15000.00", "0.00")))
    assert first.paid_percent == 63
    assert second.paid_percent == 83
    assert report.totals.model_dump() == {
        "contract_amount": Decimal("690000.00"),
        "active_works_amount": Decimal("590000.00"),
        "paid": Decimal("390000.00"),
        "remaining": Decimal("200000.00"),
        "unallocated": Decimal("0.00"),
    }

    assert [
        (
            work.work_id,
            work.status,
            str(work.price),
            str(work.paid),
            str(work.remaining),
        )
        for work in first.works
    ] == [
        ("W-11", "done", "100000.00", "100000.00", "0.00"),
        ("W-12", "done", "100000.00", "100000.00", "0.00"),
        ("W-13", "cancelled", "100000.00", "0.00", "0.00"),
        ("W-14", "done", "100000.00", "100000.00", "0.00"),
        ("W-15", "planned", "100000.00", "15000.00", "85000.00"),
        ("W-16", "planned", "100000.00", "0.00", "100000.00"),
    ]
    assert [
        (work.work_id, work.status, str(work.paid), str(work.remaining))
        for work in second.works
    ] == [
        ("W-21", "done", "20000.00", "0.00"),
        ("W-22", "done", "30000.00", "0.00"),
        ("W-23", "planned", "25000.00", "15000.00"),
    ]


def test_refund_counts_after_payment_but_not_on_refund_date(
    connection: sqlite3.Connection,
) -> None:
    before_refund = build_report(connection, date(2026, 9, 9))
    on_refund = build_report(connection, date(2026, 9, 10))

    assert _contract(before_refund, "D-1").paid == Decimal("350000.00")
    assert _contract(on_refund, "D-1").paid == Decimal("300000.00")


def test_queued_future_and_overpayments_are_separate(
    connection: sqlite3.Connection,
) -> None:
    on_tenth = build_report(connection, date(2026, 11, 10))
    on_twelfth = build_report(connection, date(2026, 11, 12))

    assert _contract(on_tenth, "D-1").paid == Decimal("315000.00")
    assert _contract(on_tenth, "D-2").paid == Decimal("75000.00")
    second = _contract(on_twelfth, "D-2")
    assert second.paid == Decimal("95000.00")
    assert second.remaining == Decimal("0.00")
    assert second.unallocated == Decimal("5000.00")
    assert _work(on_twelfth, "W-23").paid == Decimal("40000.00")


def test_work_statuses_use_event_dates_inclusively(
    connection: sqlite3.Connection,
) -> None:
    before_cancel = build_report(connection, date(2026, 10, 11))
    on_cancel = build_report(connection, date(2026, 10, 12))
    before_completion = build_report(connection, date(2026, 11, 10))
    on_completion = build_report(connection, date(2026, 11, 11))

    assert _work(before_cancel, "W-13").status == "planned"
    assert _work(on_cancel, "W-13").status == "cancelled"
    assert _work(before_completion, "W-23").status == "planned"
    assert _work(on_completion, "W-23").status == "done"


def test_large_amounts_and_kopecks_remain_exact(data_dir: Path, tmp_path: Path) -> None:
    contracts_path = data_dir / "contracts.csv"
    contracts_path.write_text(
        contracts_path.read_text(encoding="utf-8").replace(
            'D-2,"Иван Петров, дизайнер",90000.00',
            'D-2,"Иван Петров, дизайнер",1234567890123456.01',
        ),
        encoding="utf-8",
    )
    payments_path = data_dir / "payments.csv"
    with payments_path.open("a", encoding="utf-8", newline="") as source:
        source.write("P-9,D-2,,Копейка,0.01,paid,2026-11-03,2026-11-03,\n")

    initialize_database(tmp_path / "money.db", data_dir)
    with connect(tmp_path / "money.db") as connection:
        report = build_report(connection, date(2026, 11, 10))

    second = _contract(report, "D-2")
    assert second.contract_amount == Decimal("1234567890123456.01")
    assert second.paid == Decimal("75000.01")
    assert _work(report, "W-23").paid == Decimal("25000.01")
    assert _work(report, "W-23").remaining == Decimal("14999.99")


def test_invalid_reload_keeps_previous_data(
    data_dir: Path, connection: sqlite3.Connection
) -> None:
    payments_path = data_dir / "payments.csv"
    payments_path.write_text(
        payments_path.read_text(encoding="utf-8").replace("300000.00", "300000.001", 1),
        encoding="utf-8",
    )

    with pytest.raises(DataError, match="доли копейки"):
        load_data(connection, data_dir)

    assert _contract(
        build_report(connection, date(2026, 11, 10)), "D-1"
    ).paid == Decimal("315000.00")


@pytest.mark.parametrize(
    ("filename", "old", "new", "message"),
    [
        (
            "contracts.csv",
            'D-2,"Иван Петров, дизайнер"',
            'D-1,"Иван Петров, дизайнер"',
            "повторяющийся договор",
        ),
        ("payments.csv", "P-3,D-1,W-14", "P-3,D-2,W-14", "другому договору"),
    ],
)
def test_invalid_references_and_duplicates_are_rejected(
    data_dir: Path, filename: str, old: str, new: str, message: str
) -> None:
    path = data_dir / filename
    path.write_text(
        path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8"
    )

    with pytest.raises(DataError, match=message):
        initialize_database(data_dir / "invalid.db", data_dir)

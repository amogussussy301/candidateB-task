import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.schemas import ContractReport, Report, ReportTotals, WorkReport


@dataclass(slots=True)
class _Work:
    work_id: str
    title: str
    status: str
    price: int
    paid: int = 0

    @property
    def remaining(self) -> int:
        return self.price - self.paid if self.status != "cancelled" else 0


def build_report(connection: sqlite3.Connection, report_date: date) -> Report:
    contracts = connection.execute(
        "SELECT * FROM contracts ORDER BY contract_id"
    ).fetchall()
    reports = [
        _build_contract_report(connection, contract, report_date)
        for contract in contracts
    ]
    totals = ReportTotals(
        contract_amount=sum(
            (contract.contract_amount for contract in reports), Decimal(0)
        ),
        active_works_amount=sum(
            (contract.active_works_amount for contract in reports), Decimal(0)
        ),
        paid=sum((contract.paid for contract in reports), Decimal(0)),
        remaining=sum((contract.remaining for contract in reports), Decimal(0)),
        unallocated=sum((contract.unallocated for contract in reports), Decimal(0)),
    )
    return Report(report_date=report_date, contracts=reports, totals=totals)


def _build_contract_report(
    connection: sqlite3.Connection, contract: sqlite3.Row, report_date: date
) -> ContractReport:
    rows = connection.execute(
        "SELECT * FROM works WHERE contract_id = ? ORDER BY position",
        (contract["contract_id"],),
    ).fetchall()
    works = [
        _Work(
            work_id=row["work_id"],
            title=row["title"],
            status=_status_on_date(row, report_date),
            price=row["price_kopecks"],
        )
        for row in rows
    ]
    active = {work.work_id: work for work in works if work.status != "cancelled"}
    payments = connection.execute(
        "SELECT * FROM payments WHERE contract_id = ? ORDER BY position",
        (contract["contract_id"],),
    ).fetchall()

    general_amount = 0
    unallocated = 0
    for payment in payments:
        amount = _effective_amount(payment, report_date)
        if amount == 0:
            continue
        work_id = payment["work_id"]
        if work_id is None:
            general_amount += amount
            continue
        if work_id not in active:
            unallocated += amount
            continue
        work = active[work_id]
        allocated = min(work.remaining, amount)
        work.paid += allocated
        unallocated += amount - allocated

    for work in active.values():
        allocated = min(work.remaining, general_amount)
        work.paid += allocated
        general_amount -= allocated
    unallocated += general_amount

    work_reports = [
        WorkReport(
            work_id=work.work_id,
            title=work.title,
            status=work.status,
            price=_money(work.price),
            paid=_money(work.paid),
            remaining=_money(work.remaining),
        )
        for work in works
    ]
    active_works_amount = sum(work.price for work in active.values())
    allocated_paid = sum(work.paid for work in works)
    remaining = sum(work.remaining for work in active.values())
    paid_percent = (
        (active_works_amount - remaining) * 100 // active_works_amount
        if active_works_amount
        else 0
    )
    return ContractReport(
        contract_id=contract["contract_id"],
        contractor=contract["contractor"],
        contract_amount=_money(contract["amount_kopecks"]),
        active_works_amount=_money(active_works_amount),
        paid=_money(allocated_paid + unallocated),
        remaining=_money(remaining),
        unallocated=_money(unallocated),
        paid_percent=paid_percent,
        works=work_reports,
    )


def _status_on_date(work: sqlite3.Row, report_date: date) -> str:
    cancelled_at = work["cancelled_at"]
    completed_at = work["completed_at"]
    if cancelled_at and date.fromisoformat(cancelled_at) <= report_date:
        return "cancelled"
    if completed_at and date.fromisoformat(completed_at) <= report_date:
        return "done"
    return "planned"


def _effective_amount(payment: sqlite3.Row, report_date: date) -> int:
    paid_at = payment["paid_at"]
    if payment["status"] == "queued" or not paid_at:
        return 0
    if date.fromisoformat(paid_at) > report_date:
        return 0
    refunded_at = payment["refunded_at"]
    if refunded_at and date.fromisoformat(refunded_at) <= report_date:
        return 0
    return payment["amount_kopecks"]


def _money(kopecks: int) -> Decimal:
    rubles, remainder = divmod(kopecks, 100)
    return Decimal(f"{rubles}.{remainder:02d}")

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class WorkReport(BaseModel):
    work_id: str
    title: str
    status: Literal["planned", "done", "cancelled"]
    price: Decimal
    paid: Decimal
    remaining: Decimal


class ContractReport(BaseModel):
    contract_id: str
    contractor: str
    contract_amount: Decimal
    active_works_amount: Decimal
    paid: Decimal
    remaining: Decimal
    unallocated: Decimal
    paid_percent: int
    works: list[WorkReport]


class ReportTotals(BaseModel):
    contract_amount: Decimal
    active_works_amount: Decimal
    paid: Decimal
    remaining: Decimal
    unallocated: Decimal


class Report(BaseModel):
    report_date: date
    contracts: list[ContractReport]
    totals: ReportTotals

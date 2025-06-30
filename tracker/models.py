from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, List, Literal


TransactionType = Literal["income", "expense"]


@dataclass
class BudgetCategory:
    name: str
    monthly_limit: Optional[float] = None
    transactions: List[Transaction] = field(default_factory=list)


@dataclass
class Transaction:
    amount: float
    t_type: TransactionType
    t_date: date
    is_rec: bool = False
    rec_interval: str | None = None
    desc: str = ""
    category: Optional[BudgetCategory] = None


@dataclass
class BalanceCheckpoint:
    date: date
    amount: float


budget_categories: list[BudgetCategory] = []
transactions: list[Transaction] = []
balance_history: list[BalanceCheckpoint] = []

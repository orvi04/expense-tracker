from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional

from tracker.models import (
    TransactionType, Transaction, BudgetCategory, BalanceCheckpoint, transactions, budget_categories, balance_history
)


def add_budget_category(name: str, limit: Optional[float] = None):
    for cat in budget_categories:
        if cat.name == name:
            return

    budget_categories.append(BudgetCategory(name, limit))


def delete_budget_category(category_name: str) -> bool:
    global budget_categories, transactions

    count = len(budget_categories)
    budget_categories[:] = [cat for cat in budget_categories if cat.name != category_name]

    if len(budget_categories) == count:
        return False

    for t in transactions:
        if t.category:
            if t.category.name == category_name:
                t.category = None

    return True


def find_or_create_category(name: str) -> BudgetCategory:
    for cat in budget_categories:
        if cat.name == name:
            return cat
    new_cat = BudgetCategory(name)
    budget_categories.append(new_cat)
    return new_cat


def add_transaction(
        amount: float,
        t_type: TransactionType,
        t_date: date,
        category_name: Optional[str] = None,
        is_rec: bool = False,
        rec_interval: str = None,
        desc: str = "",
) -> None:
    category = None
    if category_name:
        category = find_or_create_category(category_name)

    transaction = Transaction(
        amount=amount,
        t_type=t_type,
        t_date=t_date,
        is_rec=is_rec,
        rec_interval=rec_interval,
        desc=desc,
        category=category
    )
    transactions.append(transaction)
    if category is not None:
        category.transactions.append(transaction)


def delete_transaction(transaction_id: int) -> bool:
    global transactions

    for i, t in enumerate(transactions):
        if t.id == transaction_id:
            if t.category:
                t.category.transactions = [tr for tr in t.category.transactions if tr.id != transaction_id]
            transactions.pop(i)
            return True
    return False


def delete_transactions_by_criteria(
        amount: Optional[float] = None,
        t_type: Optional[TransactionType] = None,
        date_range: Optional[tuple[date, date]] = None,
        category_name: Optional[str] = None
) -> int:
    global transactions

    to_delete = []
    for t in transactions:
        if ((amount is None or t.amount == amount) and
                (t_type is None or t.t_type == t_type) and
                (date_range is None or (date_range[0] <= t.t_date <= date_range[1])) and
                (category_name is None or (t.category and t.category.name == category_name))):
            to_delete.append(t.id)
    initial_count = len(transactions)
    transactions = [t for t in transactions if t.id not in to_delete]

    for cat in budget_categories:
        cat.transactions = [t for t in cat.transactions if t.id not in to_delete]

    return initial_count - len(transactions)


def set_timeframe(
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
) -> tuple[str, date | int]:
    if day is not None:
        timeframe = "day"
        target_date = date(year or date.today().year,
                           month or date.today().month,
                           day)
    elif month is not None:
        timeframe = "month"
        target_date = date(year or date.today().year, month, 1)
    elif year is not None:
        timeframe = "year"
        target_date = year
    else:
        timeframe = "day"
        target_date = date.today()

    return timeframe, target_date


def check_spending(day: Optional[int] = None, month: Optional[int] = None, year: Optional[int] = None):
    timeframe, target_date = set_timeframe(year, month, day)

    total = {
        "expense": 0.0,
        "income": 0.0,
        "net": 0.0
    }

    categories = {
        category.name: {
            "income": 0.0,
            "expense": 0.0,
            "net": 0.0
        } for category in budget_categories
    }

    for t in transactions:
        if timeframe == "day" and t.t_date == target_date:
            pass
        elif timeframe == "month":
            if not (t.t_date.year == target_date.year and
                    t.t_date.month == target_date.month):
                continue
        elif timeframe == "year":
            if t.t_date.year != target_date:
                continue

        total[t.t_type] += t.amount
        if t.category.name in categories:
            categories[t.category.name][t.t_type] += t.amount
            categories[t.category.name]["net"] += t.amount if t.t_type == "income" else -t.amount

    total["net"] = total["income"] - total["expense"]

    return {
        "timeframe": timeframe,
        "target_date": target_date.isoformat() if hasattr(target_date, "isoformat") else target_date,
        "totals": total,
        "categories": categories
    }


def update_bal(bal, t_amount, t_type):
    if t_type == "income":
        bal += t_amount
    else:
        bal -= t_amount
    return round(bal, 2)


def set_balance_checkpoint(cp_date: date, amount: float):
    balance_history[:] = [cp for cp in balance_history if cp.date != cp_date]
    balance_history.append(BalanceCheckpoint(cp_date, amount))
    balance_history.sort(key=lambda x: x.date)


def get_nearest_checkpoint(target_date: date) -> BalanceCheckpoint | None:
    valid_cps = [cp for cp in balance_history if cp.date <= target_date]
    if not valid_cps:
        return None
    return max(valid_cps, key=lambda x: x.date)


def calc_proj_bal(target_date: date) -> float:
    bal_cp = get_nearest_checkpoint(target_date)
    cp_valid = get_nearest_checkpoint(target_date) is not None

    if cp_valid:
        balance = bal_cp.amount
        c_date = bal_cp.date
    else:
        balance = 0
        c_date = min(
            min((transaction.t_date for transaction in transactions), default=date.today()), date.today()
        )

    while c_date <= target_date:
        for transaction in transactions:
            if transaction.t_date > c_date:
                continue
            if not transaction.is_rec and transaction.t_date == c_date:
                balance = update_bal(balance, transaction.amount, transaction.t_type)
            elif transaction.is_rec:
                if transaction.t_date == c_date:
                    balance = update_bal(balance, transaction.amount, transaction.t_type)
                elif c_date > transaction.t_date:
                    delta = c_date - transaction.t_date
                    if transaction.rec_interval == "daily" and delta.days > 0:
                        balance = update_bal(balance, transaction.amount, transaction.t_type)
                    elif transaction.rec_interval == "weekly" and delta.days > 0 and delta.days % 7 == 0:
                        balance = update_bal(balance, transaction.amount, transaction.t_type)
                    elif transaction.rec_interval == "monthly":
                        months_diff = (c_date.year - transaction.t_date.year) * 12 + \
                                      (c_date.month - transaction.t_date.month)
                        if months_diff > 0:
                            expected_date = transaction.t_date + relativedelta(months=months_diff)
                            if c_date == expected_date:
                                balance = update_bal(balance, transaction.amount, transaction.t_type)
                    elif transaction.rec_interval == "yearly":
                        is_leap = c_date.year % 4 and (c_date.year % 100 != 0 or c_date.year % 400 == 0)
                        if transaction.t_date.month == 2 and transaction.t_date.day == 29:
                            if is_leap and c_date.month == 2 and c_date.day == 29:
                                balance = update_bal(balance, transaction.amount, transaction.t_type)
                            elif not is_leap and c_date.month == 2 and c_date.day == 28:
                                balance = update_bal(balance, transaction.amount, transaction.t_type)
                        else:
                            if c_date.day == transaction.t_date.day and \
                                    c_date.month == transaction.t_date.month and \
                                    c_date.year > transaction.t_date.year:
                                balance = update_bal(balance, transaction.amount, transaction.t_type)

        c_date += timedelta(days=1)
    return balance

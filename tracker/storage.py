import json
from pathlib import Path
from datetime import date
from .models import transactions, balance_history, budget_categories, BudgetCategory, Transaction, BalanceCheckpoint


SAVES_DIR = Path("saves")
SAVES_DIR.mkdir(exist_ok=True)


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, BudgetCategory):
            return {
                "name": obj.name,
                "monthly_limit": obj.monthly_limit,
            }
        return super().default(obj)


def list_save_files():
    return [f.stem for f in SAVES_DIR.glob("*.json")]


def save_data(save_name="default"):
    data = {
        "metadata": {
            "version": "1.0",
            "created": date.today().isoformat()
        },
        "categories": [
            {
                "name": cat.name,
                "monthly_limit": cat.monthly_limit,
            } for cat in budget_categories
        ],
        "transactions": [
            {
                **t.__dict__,
                "category": t.category.name if t.category else None
            } for t in transactions
        ],
        "checkpoints": [c.__dict__ for c in balance_history]
    }
    json_str = json.dumps(
        data,
        cls=EnhancedJSONEncoder,
        indent=2
    )
    (SAVES_DIR / f"{save_name}.json").write_text(json_str)


def load_data(save_name="default"):
    global transactions, balance_history, budget_categories
    try:
        filepath = SAVES_DIR / f"{save_name}.json"
        data = json.loads(filepath.read_text())

        # Clear existing data
        transactions.clear()
        balance_history.clear()
        budget_categories.clear()

        # Rebuild categories
        for cat_data in data.get("categories", []):
            budget_categories.append(
                BudgetCategory(
                    name=cat_data["name"],
                    monthly_limit=cat_data.get("monthly_limit")
                )
            )

        # Helper: map category name to BudgetCategory object for quick lookup
        category_map = {cat.name: cat for cat in budget_categories}

        # Rebuild transactions and link category objects
        for t in data["transactions"]:
            category_obj = category_map.get(t["category"])
            transaction = Transaction(
                amount=t['amount'],
                t_type=t['t_type'],
                t_date=date.fromisoformat(t['t_date']),
                is_rec=t['is_rec'],
                rec_interval=t['rec_interval'],
                desc=t['desc'],
                category=category_obj
            )
            transactions.append(transaction)

            # Also update category.transactions lists
            if category_obj is not None:
                category_obj.transactions.append(transaction)

        # Rebuild balance checkpoints
        balance_history.extend(
            BalanceCheckpoint(
                date=date.fromisoformat(c['date']),
                amount=c['amount']
            ) for c in data.get("checkpoints", [])
        )

        print(f"Loaded save '{save_name}' with {len(transactions)} transactions and {len(budget_categories)} categories")
    except FileNotFoundError:
        print(f"Save file '{save_name}' not found. Starting fresh.")
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
            "created": date.today().isoformat(),
            "transaction_counter": len(transactions)
        },
        "categories": [
            {
                "name": cat.name,
                "monthly_limit": cat.monthly_limit,
                "transaction_ids": [t.id for t in cat.transactions]
            } for cat in budget_categories
        ],
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "t_type": t.t_type,
                "t_date": t.t_date.isoformat(),
                "is_rec": t.is_rec,
                "rec_interval": t.rec_interval,
                "desc": t.desc,
                "category": t.category.name if t.category else None
            } for t in transactions
        ],
        "checkpoints": [
            {
                "date": cp.date.isoformat(),
                "amount": cp.amount
            } for cp in balance_history
        ]
    }

    try:
        json_str = json.dumps(data, cls=EnhancedJSONEncoder, indent=2)
        save_path = SAVES_DIR / f"{save_name}.json"
        save_path.write_text(json_str)
        print(f"✓ Saved {len(transactions)} transactions to '{save_name}'")
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False


def load_data(save_name="default"):
    global transactions, balance_history, budget_categories
    try:
        filepath = SAVES_DIR / f"{save_name}.json"
        if not filepath.exists():
            print(f"Save file '{save_name}' not found")
            return False

        data = json.loads(filepath.read_text())

        transactions.clear()
        balance_history.clear()
        budget_categories.clear()

        category_map = {}
        for cat_data in data.get("categories", []):
            new_cat = BudgetCategory(
                name=cat_data["name"],
                monthly_limit=cat_data.get("monthly_limit")
            )
            budget_categories.append(new_cat)
            category_map[new_cat.name] = new_cat

        id_to_transaction = {}
        for t_data in data.get("transactions", []):
            try:
                transaction = Transaction(
                    id=t_data["id"],
                    amount=t_data["amount"],
                    t_type=t_data["t_type"],
                    t_date=date.fromisoformat(t_data["t_date"]),
                    is_rec=t_data["is_rec"],
                    rec_interval=t_data["rec_interval"],
                    desc=t_data["desc"],
                    category=category_map.get(t_data["category"]) if t_data.get("category") else None
                )
                transactions.append(transaction)
                id_to_transaction[transaction.id] = transaction
            except Exception as e:
                print(f"Warning: Skipping invalid transaction {t_data.get('id')}: {e}")

        # 3. Rebuild category transaction lists
        for cat_data in data.get("categories", []):
            if cat_data["name"] in category_map:
                category_map[cat_data["name"]].transactions = [
                    id_to_transaction[t_id]
                    for t_id in cat_data.get("transaction_ids", [])
                    if t_id in id_to_transaction
                ]

        # 4. Restore balance checkpoints
        for cp_data in data.get("checkpoints", []):
            try:
                balance_history.append(BalanceCheckpoint(
                    date=date.fromisoformat(cp_data["date"]),
                    amount=cp_data["amount"]
                ))
            except Exception as e:
                print(f"Warning: Skipping invalid checkpoint: {e}")

        print(f"✓ Loaded {len(transactions)} transactions, {len(budget_categories)} categories")
        return True

    except Exception as e:
        print(f"Error loading data: {e}")
        # Clear partial load on failure
        transactions.clear()
        balance_history.clear()
        budget_categories.clear()
        return False
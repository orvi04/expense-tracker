from tracker.logic import add_budget_category, delete_budget_category, add_transaction, check_spending
from tracker.models import budget_categories, transactions
from tracker.storage import save_data, load_data
from datetime import date

# Reset state
budget_categories.clear()
transactions.clear()

# Create and test categories
add_budget_category("Food", 250.0)
add_budget_category("Salary", None)

# Add a transaction
add_transaction(1000, "income", date(2025, 6, 1), category_name="Salary")
add_transaction(100, "expense", date(2025, 6, 2), category_name="Food")

# Check spending
report = check_spending(month=6, year=2025)
print("Spending report for June 2025:")
print(report)

# Save test
save_data("test_cli_data")

# Clear and load
budget_categories.clear()
transactions.clear()
load_data("test_cli_data")

# Confirm restore
print("After loading:")
print([cat.name for cat in budget_categories])
print([(t.amount, t.category.name if t.category else None) for t in transactions])

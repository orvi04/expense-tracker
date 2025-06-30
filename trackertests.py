import unittest
import json
import os
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
#from tracker import *
from tracker.models import (
    TransactionType, Transaction, BudgetCategory,
    BalanceCheckpoint, budget_categories, transactions, balance_history
)

from tracker.logic import (
    add_budget_category, delete_budget_category, find_or_create_category,
    add_transaction, check_spending, set_balance_checkpoint, get_nearest_checkpoint,
    calc_proj_bal
)

from tracker.storage import (
    save_data, load_data, list_save_files, SAVES_DIR
)



class TestBudgetTracker(unittest.TestCase):
    def setUp(self):
        """Reset global state before each test"""
        budget_categories.clear()
        transactions.clear()
        balance_history.clear()

        # Clear any test saves
        for f in SAVES_DIR.glob("test_*.json"):
            f.unlink()

    def test_budget_category_creation(self):
        """Test BudgetCategory dataclass"""
        cat = BudgetCategory("Groceries", 500.0)
        self.assertEqual(cat.name, "Groceries")
        self.assertEqual(cat.monthly_limit, 500.0)
        self.assertEqual(len(cat.transactions), 0)

    def test_transaction_creation(self):
        """Test Transaction dataclass"""
        cat = BudgetCategory("Utilities")
        trans = Transaction(
            amount=100.0,
            t_type="expense",
            t_date=date(2023, 1, 15),
            is_rec=True,
            rec_interval="monthly",
            desc="Electric bill",
            category=cat
        )
        self.assertEqual(trans.amount, 100.0)
        self.assertEqual(trans.t_type, "expense")
        self.assertEqual(trans.t_date, date(2023, 1, 15))
        self.assertTrue(trans.is_rec)
        self.assertEqual(trans.rec_interval, "monthly")
        self.assertEqual(trans.desc, "Electric bill")
        self.assertEqual(trans.category, cat)

    def test_add_budget_category(self):
        """Test adding budget categories"""
        add_budget_category("Food", 300.0)
        self.assertEqual(len(budget_categories), 1)
        self.assertEqual(budget_categories[0].name, "Food")
        self.assertEqual(budget_categories[0].monthly_limit, 300.0)

        # Test duplicate prevention
        add_budget_category("Food", 400.0)
        self.assertEqual(len(budget_categories), 1)
        self.assertEqual(budget_categories[0].monthly_limit, 300.0)

    def test_delete_budget_category(self):
        """Test deleting budget categories"""
        add_budget_category("Food")
        add_budget_category("Transport")

        # Add transactions with categories
        add_transaction(50.0, "expense", date(2023, 1, 1), "Food")
        add_transaction(30.0, "expense", date(2023, 1, 2), "Transport")

        self.assertEqual(len(budget_categories), 2)
        self.assertEqual(len(transactions), 2)

        # Delete category
        result = delete_budget_category("Food")
        self.assertTrue(result)
        self.assertEqual(len(budget_categories), 1)  # Only "Transport" remains
        self.assertEqual(budget_categories[0].name, "Transport")

        # Verify transactions were updated
        for t in transactions:
            if t.amount == 50.0:  # The Food transaction
                self.assertIsNone(t.category)

        # Test deleting non-existent category
        result = delete_budget_category("NonExistent")
        self.assertFalse(result)

    def test_find_or_create_category(self):
        """Test finding or creating categories"""
        cat1 = find_or_create_category("Food")
        self.assertEqual(len(budget_categories), 1)
        self.assertEqual(cat1.name, "Food")

        cat2 = find_or_create_category("Food")
        self.assertEqual(cat1, cat2)
        self.assertEqual(len(budget_categories), 1)

        cat3 = find_or_create_category("Transport")
        self.assertEqual(len(budget_categories), 2)

    def test_add_transaction(self):
        """Test adding transactions"""
        add_transaction(
            amount=100.0,
            t_type="income",
            t_date=date(2023, 1, 1),
            category_name="Salary",
            is_rec=True,
            rec_interval="monthly",
            desc="Monthly salary"
        )

        self.assertEqual(len(transactions), 1)
        trans = transactions[0]
        self.assertEqual(trans.amount, 100.0)
        self.assertEqual(trans.t_type, "income")
        self.assertEqual(trans.t_date, date(2023, 1, 1))
        self.assertTrue(trans.is_rec)
        self.assertEqual(trans.rec_interval, "monthly")
        self.assertEqual(trans.desc, "Monthly salary")

        # Verify category was created and linked
        self.assertEqual(len(budget_categories), 1)
        self.assertEqual(trans.category.name, "Salary")
        self.assertEqual(len(trans.category.transactions), 1)
        self.assertEqual(trans.category.transactions[0], trans)

    def test_check_spending_daily(self):
        """Test checking spending for a day"""
        add_transaction(100.0, "income", date(2023, 1, 1), "Salary")
        add_transaction(50.0, "expense", date(2023, 1, 1), "Food")
        add_transaction(30.0, "expense", date(2023, 1, 1), "Food")  # Same day

        result = check_spending(day=1, month=1, year=2023)

        self.assertEqual(result["timeframe"], "day")
        self.assertEqual(result["target_date"], "2023-01-01")
        self.assertEqual(result["totals"]["income"], 100.0)
        self.assertEqual(result["totals"]["expense"], 80.0)  # 50 + 30
        self.assertEqual(result["totals"]["net"], 20.0)  # 100 - 80

    def test_check_spending_monthly(self):
        """Test checking spending for a month"""
        add_transaction(100.0, "income", date(2023, 1, 1), "Salary")
        add_transaction(50.0, "expense", date(2023, 1, 15), "Food")
        add_transaction(30.0, "expense", date(2023, 2, 1), "Food")  # Different month

        result = check_spending(month=1, year=2023)

        self.assertEqual(result["timeframe"], "month")
        self.assertEqual(result["target_date"], "2023-01-01")
        self.assertEqual(result["totals"]["income"], 100.0)
        self.assertEqual(result["totals"]["expense"], 50.0)
        self.assertEqual(result["totals"]["net"], 50.0)

        self.assertEqual(result["categories"]["Salary"]["income"], 100.0)
        self.assertEqual(result["categories"]["Food"]["expense"], 50.0)

    def test_check_spending_yearly(self):
        """Test checking spending for a year"""
        add_transaction(1200.0, "income", date(2023, 1, 1), "Salary")
        add_transaction(600.0, "expense", date(2023, 6, 15), "Food")
        add_transaction(30.0, "expense", date(2022, 12, 31), "Food")  # Different year

        result = check_spending(year=2023)

        self.assertEqual(result["timeframe"], "year")
        self.assertEqual(result["target_date"], 2023)
        self.assertEqual(result["totals"]["income"], 1200.0)
        self.assertEqual(result["totals"]["expense"], 600.0)
        self.assertEqual(result["totals"]["net"], 600.0)

        self.assertEqual(result["categories"]["Salary"]["income"], 1200.0)
        self.assertEqual(result["categories"]["Food"]["expense"], 600.0)

    def test_balance_checkpoints(self):
        """Test balance checkpoint functionality"""
        set_balance_checkpoint(date(2023, 1, 1), 1000.0)
        set_balance_checkpoint(date(2023, 6, 1), 1500.0)

        self.assertEqual(len(balance_history), 2)
        self.assertEqual(balance_history[0].date, date(2023, 1, 1))
        self.assertEqual(balance_history[0].amount, 1000.0)

        # Test updating existing checkpoint
        set_balance_checkpoint(date(2023, 1, 1), 1200.0)
        self.assertEqual(len(balance_history), 2)
        self.assertEqual(balance_history[0].amount, 1200.0)

    def test_get_nearest_checkpoint(self):
        """Test finding nearest balance checkpoint"""
        set_balance_checkpoint(date(2023, 1, 1), 1000.0)
        set_balance_checkpoint(date(2023, 6, 1), 1500.0)

        # Exact match
        cp = get_nearest_checkpoint(date(2023, 6, 1))
        self.assertEqual(cp.amount, 1500.0)

        # Before first checkpoint
        cp = get_nearest_checkpoint(date(2022, 12, 31))
        self.assertIsNone(cp)

        # Between checkpoints
        cp = get_nearest_checkpoint(date(2023, 3, 15))
        self.assertEqual(cp.amount, 1000.0)

        # After last checkpoint
        cp = get_nearest_checkpoint(date(2023, 12, 31))
        self.assertEqual(cp.amount, 1500.0)

    def test_calc_proj_bal_no_checkpoint(self):
        """Test balance projection without checkpoints"""
        add_transaction(100.0, "income", date(2023, 1, 1))
        add_transaction(50.0, "expense", date(2023, 1, 2))

        # Projection for date before any transactions
        bal = calc_proj_bal(date(2022, 12, 31))
        self.assertEqual(bal, 0.0)

        # Projection for date after transactions
        bal = calc_proj_bal(date(2023, 1, 3))
        self.assertEqual(bal, 50.0)

    def test_calc_proj_bal_with_checkpoint(self):
        """Test balance projection with checkpoints"""
        set_balance_checkpoint(date(2023, 1, 1), 1000.0)
        add_transaction(100.0, "income", date(2023, 1, 2))
        add_transaction(50.0, "expense", date(2023, 1, 3))

        bal = calc_proj_bal(date(2023, 1, 4))
        self.assertEqual(bal, 1050.0)

    def test_calc_proj_bal_recurring(self):
        """Test balance projection with recurring transactions"""
        # Monthly income starting Jan 1
        add_transaction(
            1000.0, "income", date(2023, 1, 1),
            is_rec=True, rec_interval="monthly"
        )

        # Monthly expense starting Feb 1
        add_transaction(
            500.0, "expense", date(2023, 2, 1),
            is_rec=True, rec_interval="monthly"
        )

        # Project to March 1
        bal = calc_proj_bal(date(2023, 3, 1))
        # Jan income: 1000
        # Feb income: 1000 (recurring)
        # Feb expense: 500
        # March income: 1000 (recurring)
        # March expense: 500 (recurring)
        # Total: 1000 + 1000 - 500 + 1000 - 500 = 2000
        self.assertEqual(bal, 2000.0)

        # Monthly expense starting Feb 1
        add_transaction(
            500.0, "expense", date(2023, 2, 1),
            is_rec=True, rec_interval="monthly"
        )

        # Project to March 1
        bal = calc_proj_bal(date(2023, 3, 1))
        self.assertEqual(bal, 1000.0)  # Jan + Feb income - Feb expense

    def test_save_and_load_data(self):
        """Test saving and loading data"""
        # Create test data
        add_budget_category("Food", 300.0)
        add_transaction(100.0, "income", date(2023, 1, 1), "Food")
        set_balance_checkpoint(date(2023, 1, 1), 1000.0)

        # Save
        save_name = "test_save"
        save_data(save_name)

        # Clear current data
        budget_categories.clear()
        transactions.clear()
        balance_history.clear()

        # Load
        load_data(save_name)

        # Verify data was restored
        self.assertEqual(len(budget_categories), 1)
        self.assertEqual(budget_categories[0].name, "Food")
        self.assertEqual(budget_categories[0].monthly_limit, 300.0)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].amount, 100.0)
        # Category name should match but won't be the same object
        self.assertEqual(transactions[0].category.name, "Food")

        self.assertEqual(len(balance_history), 1)
        self.assertEqual(balance_history[0].amount, 1000.0)

    def test_list_save_files(self):
        """Test listing save files"""
        # Create test saves
        save_data("test_save1")
        save_data("test_save2")

        saves = list_save_files()
        self.assertIn("test_save1", saves)
        self.assertIn("test_save2", saves)

    def test_edge_cases(self):
        """Test various edge cases"""
        # Empty category name
        add_budget_category("", 100.0)
        self.assertEqual(len(budget_categories), 1)
        self.assertEqual(budget_categories[0].name, "")

        # Zero amount transaction
        add_transaction(0.0, "income", date.today())
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].amount, 0.0)

        # Future date transaction
        future_date = date.today() + timedelta(days=365)
        add_transaction(100.0, "income", future_date)
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[1].t_date, future_date)

        # Negative amount (should be allowed as it's just a number)
        add_transaction(-50.0, "expense", date.today())
        self.assertEqual(len(transactions), 3)
        self.assertEqual(transactions[2].amount, -50.0)

    def test_leap_year_recurring(self):
        """Test recurring transactions around leap years"""
        # Yearly transaction on Feb 29
        add_transaction(
            100.0, "income", date(2020, 2, 29),
            is_rec=True, rec_interval="yearly"
        )

        # Check 2021 (not a leap year)
        bal = calc_proj_bal(date(2021, 2, 28))
        self.assertEqual(bal, 100.0)

        # Check 2024 (leap year)
        bal = calc_proj_bal(date(2024, 2, 29))
        self.assertEqual(bal, 200.0)

    def test_cleanup(self):
        """Clean up any test files"""
        for f in SAVES_DIR.glob("test_*.json"):
            f.unlink()

if __name__ == "__main__":
    unittest.main()
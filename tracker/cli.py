import cmd
from datetime import date
from typing import Optional
from tracker.logic import (
    add_budget_category,
    delete_budget_category,
    add_transaction,
    check_spending,
    calc_proj_bal,
    set_balance_checkpoint,
    delete_transaction,
    delete_transactions_by_criteria
)
from tracker.storage import save_data, load_data, list_save_files
from tracker.models import budget_categories, transactions, balance_history


class ExpenseTrackerCLI(cmd.Cmd):
    prompt = "(tracker) "

    def __init__(self):
        super().__init__()
        self.intro = "Welcome to Expense Tracker. Type 'help' for commands."

    # ===== CORE COMMANDS =====
    def do_add(self, arg):
        """Add a transaction: add <amount> <income|expense> [category] [date=YYYY-MM-DD] [--recurring] [--desc]"""
        try:
            args = self._parse_add_args(arg)
            add_transaction(
                amount=args['amount'],
                t_type=args['type'],
                t_date=args['date'],
                category_name=args['category'],
                is_rec=args['recurring'],
                desc=args['desc']
            )
            print(f"✓ Added {args['type']} of ${args['amount']:.2f}")
        except Exception as e:
            print(f"Error: {e}")

    def do_balance(self, arg):
        """View current balance and spending summary"""
        try:
            # Current balance
            balance = calc_proj_bal(date.today())
            print(f"\nCurrent Balance: ${balance:.2f}")

            # Monthly summary
            monthly = check_spending(month=date.today().month, year=date.today().year)
            print(f"\nMonthly Summary ({monthly['target_date'][:7]}):")
            print(f"  Income: ${monthly['totals']['income']:.2f}")
            print(f"  Expenses: ${monthly['totals']['expense']:.2f}")
            print(f"  Net: ${monthly['totals']['net']:.2f}")

            # Category breakdown
            if monthly['categories']:
                print("\nCategories:")
                for cat, data in monthly['categories'].items():
                    print(f"  {cat}: ${data['net']:.2f} (I: ${data['income']:.2f}, E: ${data['expense']:.2f})")
        except Exception as e:
            print(f"Error: {e}")

    def do_delete(self, arg):
        """Delete transactions: delete <ID> OR delete --filter <criteria>"""
        args = arg.split()

        if not args:
            print("Usage:\n  delete <ID>\n  delete --filter [--amount X] [--type income|expense] [--from DATE] [--to DATE] [--category NAME]")
            return

        try:
            if args[0].isdigit():  # Delete by ID
                if delete_transaction(int(args[0])):
                    print(f"✓ Deleted transaction {args[0]}")
                else:
                    print("Transaction not found")
            elif args[0] == "--filter":  # Filter deletion
                deleted_count = self._delete_by_filter(args[1:])
                print(f"✓ Deleted {deleted_count} transactions")
            else:
                print("Invalid command")
        except Exception as e:
            print(f"Error: {e}")

    def _delete_by_filter(self, args) -> int:
        """Helper for filter-based deletion"""
        filters = {
            'amount': None,
            't_type': None,
            'date_range': None,
            'category_name': None
        }

        i = 0
        while i < len(args):
            if args[i] == "--amount":
                filters['amount'] = float(args[i+1])
                i += 2
            elif args[i] == "--type":
                filters['t_type'] = args[i+1]
                i += 2
            elif args[i] == "--from":
                start_date = date.fromisoformat(args[i+1])
                filters['date_range'] = (start_date, filters['date_range'][1] if filters['date_range'] else date.max)
                i += 2
            elif args[i] == "--to":
                end_date = date.fromisoformat(args[i+1])
                filters['date_range'] = (filters['date_range'][0] if filters['date_range'] else date.min, end_date)
                i += 2
            elif args[i] == "--category":
                filters['category_name'] = args[i+1]
                i += 2
            else:
                i += 1

        return delete_transactions_by_criteria(**filters)

    # ===== CATEGORY MANAGEMENT =====
    def do_category(self, arg):
        """Manage categories: category <add|list|delete> [name] [limit]"""
        args = arg.split()
        if not args:
            self.help_category()
            return

        try:
            if args[0] == "add":
                name = args[1]
                limit = float(args[2]) if len(args) > 2 else None
                add_budget_category(name, limit)
                print(f"✓ Added category: {name}")
            elif args[0] == "list":
                if not budget_categories:
                    print("No categories defined")
                    return
                print("\nCategories:")
                for cat in budget_categories:
                    print(f"  {cat.name}: ${cat.monthly_limit or 'No limit'}")
            elif args[0] == "delete":
                if delete_budget_category(args[1]):
                    print(f"✓ Deleted category: {args[1]}")
                else:
                    print(f"Category not found: {args[1]}")
            else:
                self.help_category()
        except Exception as e:
            print(f"Error: {e}")

    # ===== DATA MANAGEMENT =====
    def do_save(self, arg):
        """Save current data: save [name=default]"""
        name = arg.strip() or "default"
        save_data(name)
        print(f"✓ Saved as '{name}'")

    def do_load(self, arg):
        """Load saved data: load [name]"""
        saves = list_save_files()
        if not saves:
            print("No save files available")
            return

        if not arg:
            print("Available saves:")
            for i, name in enumerate(saves, 1):
                print(f"{i}. {name}")
            try:
                choice = int(input("Select save: ")) - 1
                name = saves[choice]
            except (ValueError, IndexError):
                print("Invalid selection")
                return
        else:
            name = arg

        load_data(name)

    # ===== UTILITIES =====
    def do_exit(self, arg):
        """Exit the program"""
        print("Goodbye!")
        return True

    # ===== HELPERS =====
    def _parse_add_args(self, arg):
        args = arg.split()
        if len(args) < 2:
            raise ValueError("Missing required arguments")

        result = {
            'amount': float(args[0]),
            'type': args[1].lower(),
            'category': args[2] if len(args) > 2 else None,
            'date': date.today(),
            'recurring': False,
            'desc': ""
        }

        # Parse optional flags
        i = 3
        while i < len(args):
            if args[i] == "--recurring":
                result['recurring'] = True
            elif args[i] == "--desc":
                result['desc'] = " ".join(args[i + 1:]) if i + 1 < len(args) else ""
                break
            elif "-" not in args[i]:  # Assume date
                result['date'] = date.fromisoformat(args[i])
            i += 1

        return result


if __name__ == "__main__":
    ExpenseTrackerCLI().cmdloop()

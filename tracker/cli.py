import cmd
from datetime import date
from typing import Optional
from dateutil.relativedelta import relativedelta
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
from tracker.models import budget_categories, transactions, balance_history, Transaction


class ExpenseTrackerCLI(cmd.Cmd):
    prompt = "(tracker) "

    def __init__(self):
        super().__init__()
        self.intro = "Welcome to Expense Tracker. Type 'help' for commands."

    # ===== CORE COMMANDS =====
    def do_add(self, arg):
        """Add a transaction: add <amount> <income|expense> [category] [date=YYYY-MM-DD] [--recur <daily|weekly|monthly|yearly>] [--desc "description"]"""
        try:
            args = self._parse_add_args(arg)
            add_transaction(
                amount=args['amount'],
                t_type=args['type'],
                t_date=args['date'],
                category_name=args['category'],
                is_rec=bool(args['recur_interval']),  # True if interval specified
                rec_interval=args['recur_interval'],
                desc=args['desc']
            )
            # Print confirmation with recurrence info if applicable
            confirmation = f"✓ Added {args['type']} of ${args['amount']:.2f}"
            if args['recur_interval']:
                confirmation += f" (recurring {args['recur_interval']})"
            print(confirmation)
            print(transactions)
        except ValueError as e:
            print(f"Invalid input: {e}")
        except Exception as e:
            print(f"Error adding transaction: {e}")

    def do_balance(self, arg):
        """Calculate projected balance up to specified date"""
        """balance [YYYY-MM-DD]"""
        try:
            args = self._parse_date_args(arg)
            target_date = args['date']
            print(target_date)
            balance = calc_proj_bal(target_date)

            # Improved output formatting
            print(f"\nProjected Balance on {target_date}:")
            print(f"  ${balance:,.2f}")

            if target_date < date.today():
                print("\nNote: Historical balance (includes all past transactions)")
            elif target_date == date.today():
                print("\nNote: Current balance")
            else:
                print("\nNote: Future projection (includes confirmed recurring transactions)")

        except Exception as e:
            print(f"Error calculating balance: {e}")

    def do_report(self, arg):
        """
        Generate spending report:
        report [timeframe] [date=YYYY-MM-DD|year=YYYY|month=MM] [--categories]

        Timeframes:
            --day       Daily report
            --week      Weekly report
            --month     Monthly report
            --year      Annual report

        Examples:
            report --day 2023-08-15 --categories
            report --month 8          # Current August
            report --year 2023        # Full year
        """
        try:
            args = self._parse_report_args(arg)
            result = check_spending(**args)

            # Print report header
            timeframe = args.get('timeframe', 'day')
            print(f"\n{' ' + timeframe.capitalize() + ' Report ':-^50}")
            print(f"Period: {result['target_date']}")

            # Print totals
            print(f"\nTotals:")
            print(f"  Income:   ${result['totals']['income']:.2f}")
            print(f"  Expenses: ${result['totals']['expense']:.2f}")
            print(f"  Net:      ${result['totals']['net']:.2f}")

            # Print category breakdown if requested
            if args.get('show_categories'):
                print("\nBy Category:")
                for cat, data in result['categories'].items():
                    print(f"  {cat}: ${data['net']:.2f} (Income: ${data['income']:.2f}, Expense: ${data['expense']:.2f})")

        except Exception as e:
            print(f"Error generating report: {e}")

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
        """Parse add command arguments with proper date handling"""
        args = arg.split()
        if len(args) < 2:
            raise ValueError("Missing required arguments (amount and type)")

        result = {
            'amount': float(args[0]),
            'type': args[1].lower(),
            'category': None,
            'date': date.today(),  # Default to today
            'recur_interval': None,
            'desc': ""
        }

        # Validate transaction type
        if result['type'] not in ('income', 'expense'):
            raise ValueError("Type must be 'income' or 'expense'")

        i = 2
        while i < len(args):
            if args[i] == '--recur':
                if i+1 >= len(args):
                    raise ValueError("Missing recurrence interval after --recur")
                if args[i+1] not in ('daily', 'weekly', 'monthly', 'yearly'):
                    raise ValueError("Invalid interval, use: daily/weekly/monthly/yearly")
                result['recur_interval'] = args[i+1]
                i += 2
            elif args[i] == '--desc':
                result['desc'] = ' '.join(args[i+1:]) if i+1 < len(args) else ""
                break
            elif args[i].startswith('--'):
                raise ValueError(f"Unknown flag: {args[i]}")
            else:
                # Try to parse as date first (YYYY-MM-DD)
                try:
                    result['date'] = date.fromisoformat(args[i])
                    i += 1
                    continue
                except ValueError:
                    pass

                # If not a date, treat as category (only if category not already set)
                if result['category'] is None:
                    result['category'] = args[i]
                    i += 1
                else:
                    raise ValueError(f"Unexpected argument: {args[i]}")

        return result

    @staticmethod
    def _parse_date_args(arg):
        """Parse date arguments for balance projection"""
        args = arg.split()
        result = {'date': date.today()}

        if args:
            try:
                result['date'] = date.fromisoformat(args[0])
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")

        return result

    @staticmethod
    def _parse_report_args(arg):
        """Parse arguments for spending reports"""
        args = arg.split()
        result = {
            'day': None,
            'month': None,
            'year': None,
            'show_categories': False
        }

        i = 0
        while i < len(args):
            if args[i] == '--day':
                result['timeframe'] = 'day'
                if i+1 < len(args) and not args[i+1].startswith('-'):
                    result['day'] = int(args[i+1])
                    i += 1
            elif args[i] == '--month':
                result['timeframe'] = 'month'
                if i+1 < len(args) and not args[i+1].startswith('-'):
                    result['month'] = int(args[i+1])
                    i += 1
            elif args[i] == '--year':
                result['timeframe'] = 'year'
                if i+1 < len(args) and not args[i+1].startswith('-'):
                    result['year'] = int(args[i+1])
                    i += 1
            elif args[i] == '--categories':
                result['show_categories'] = True
            i += 1

        return result


if __name__ == "__main__":
    ExpenseTrackerCLI().cmdloop()

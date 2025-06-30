# Expense Tracker CLI

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line expense tracker with budgeting features, recurring transactions, and detailed financial reporting.

## Features

- 💰 Track income and expenses
- 📊 Categorize transactions
- 🔄 Handle recurring transactions
- ❌ Delete transactions/categories
- 📅 View spending by day/month/year
- 💾 Save/Load your financial data
- 📈 Balance projections

## Installation

```bash
git clone https://github.com/your-username/expense-tracker.git
cd expense-tracker
pip install -r requirements.txt

## 📋 Complete Command Reference

### 💸 Transaction Commands
| Command | Example | Description |
|---------|---------|-------------|
| **Add Transaction**<br>`add <amount> <type> [category] [--date YYYY-MM-DD] [--recur <daily|weekly|monthly|yearly>] [--desc "notes"]` | `add 25.50 expense Coffee`<br>`add 2000 income Salary --recurring monthly`<br>`add 15.99 expense Movies --desc "Date night" --date 2023-08-20` | Record new transaction<br>Add recurring income<br>Add dated expense with notes |
| **Delete Transaction**<br>`delete <ID>`<br>`delete --filter [--type TYPE] [--category NAME] [--amount X] [--from DATE] [--to DATE]` | `delete 7`<br>`delete --filter --category Dining`<br>`delete --filter --from 2023-01-01 --to 2023-12-31 --amount 50` | Delete by transaction ID<br>Delete all dining expenses<br>Delete all $50 transactions in 2023 |

### 🗂 Category Commands
| Command | Example | Description |
|---------|---------|-------------|
| **Create Category**<br>`category add <name> [limit]` | `category add Rent 1200`<br>`category add Groceries` | New category with $1200 limit<br>Unlimited category |
| **List Categories**<br>`category list` | `category list` | Shows all categories with limits |
| **Delete Category**<br>`category delete <name>` | `category delete Streaming` | Removes category and uncategorizes its transactions |

### 📊 Reporting Commands
| Command | Example | Description |
|---------|---------|-------------|
| **View Balance**<br>`balance [YYYY-MM-DD]` | `balance`<br>`balance 2025-07-01`<br>`balance` |
| **Spending Breakdown**<br>`report [timeframe] [date=YYYY-MM-DD|year=YYYY|month=MM] [--categories]` |

### 💾 Data Commands
| Command | Example | Description |
|---------|---------|-------------|
| **Save Data**<br>`save [name]` | `save`<br>`save august_backup` | Saves to "default.json"<br>Named backup |
| **Load Data**<br>`load [name/number]` | `load 1`<br>`load september` | Load by list number<br>Load by filename |
| **List Saves**<br>`list` | `list` | Shows all save files |

### 🛠 System Commands
| Command | Description |
|---------|-------------|
| `help` | Show all available commands |
| `exit` | Quit the application |

## 🏃‍♂️ Quickstart Examples

1. **Track weekly groceries**
   ```bash
   add 85.30 expense Groceries --desc "Weekly shopping"
from tracker.cli import ExpenseTrackerCLI


def main():
    try:
        ExpenseTrackerCLI().cmdloop()
    except KeyboardInterrupt:
        print("\nUse 'exit' to quit properly")


if __name__ == "__main__":
    main()

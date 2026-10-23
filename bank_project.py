import mysql.connector
from mysql.connector import Error

class BankManagementSystem:
    def __init__(self):
        try:
            # Establish connection to MySQL
            # Update 'user' and 'password' with your local MySQL credentials
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            self.cursor = self.conn.cursor()
            self.setup_database()
        except Error as e:
            print(f"Database connection error: {e}")
            exit(1)

    def setup_database(self):
        """Creates database and required tables if they don't exist."""
        self.cursor.execute("CREATE DATABASE IF NOT EXISTS bank_db")
        self.cursor.execute("USE bank_db")
        
        # Accounts Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_number INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                balance DECIMAL(10, 2) NOT NULL
            )
        """)
        
        # Transactions Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INT AUTO_INCREMENT PRIMARY KEY,
                account_number INT,
                transaction_type VARCHAR(50),
                amount DECIMAL(10, 2),
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                balance DECIMAL(10, 2),
                FOREIGN KEY (account_number) REFERENCES accounts(account_number)
            )
        """)
        self.conn.commit()

    def create_account(self):
        try:
            name = input("Enter Customer Name: ").strip()
            if not name:
                raise ValueError("Customer name cannot be empty.")
            
            initial_deposit = float(input("Enter Initial Deposit Amount: "))
            if initial_deposit < 0:
                raise ValueError("Initial deposit cannot be negative.")

            self.cursor.execute(
                "INSERT INTO accounts (customer_name, balance) VALUES (%s, %s)",
                (name, initial_deposit)
            )
            self.conn.commit()
            acc_no = self.cursor.lastrowid

            # Log the initial deposit transaction
            self.cursor.execute(
                "INSERT INTO transactions (account_number, transaction_type, amount, balance) VALUES (%s, %s, %s, %s)",
                (acc_no, "Deposit (Initial)", initial_deposit, initial_deposit)
            )
            self.conn.commit()
            print(f"\nAccount created successfully! Your Account Number is: {acc_no}")
        except ValueError as ve:
            print(f"Invalid Input: {ve}")
        except Error as e:
            self.conn.rollback()
            print(f"Database Error: {e}")

    def get_account(self, acc_no):
        self.cursor.execute("SELECT account_number, customer_name, balance FROM accounts WHERE account_number = %s", (acc_no,))
        return self.cursor.fetchone()

    def check_balance(self):
        try:
            acc_no = int(input("Enter Account Number: "))
            account = self.get_account(acc_no)
            if account:
                print(f"\nAccount Holder: {account[1]}")
                print(f"Current Balance: ${account[2]:.2f}")
            else:
                print("Account not found.")
        except ValueError:
            print("Please enter a valid integer account number.")

    def deposit(self):
        try:
            acc_no = int(input("Enter Account Number: "))
            account = self.get_account(acc_no)
            if not account:
                print("Account not found.")
                return

            amount = float(input("Enter amount to deposit: "))
            if amount <= 0:
                raise ValueError("Deposit amount must be greater than zero.")

            new_balance = float(account[2]) + amount

            self.cursor.execute("UPDATE accounts SET balance = %s WHERE account_number = %s", (new_balance, acc_no))
            self.cursor.execute(
                "INSERT INTO transactions (account_number, transaction_type, amount, balance) VALUES (%s, %s, %s, %s)",
                (acc_no, "Deposit", amount, new_balance)
            )
            self.conn.commit()
            print(f"\nSuccessfully deposited ${amount:.2f}. New Balance: ${new_balance:.2f}")
        except ValueError as ve:
            print(f"Invalid Input: {ve}")
        except Error as e:
            self.conn.rollback()
            print(f"Database Error: {e}")

    def withdraw(self):
        try:
            acc_no = int(input("Enter Account Number: "))
            account = self.get_account(acc_no)
            if not account:
                print("Account not found.")
                return

            amount = float(input("Enter amount to withdraw: "))
            if amount <= 0:
                raise ValueError("Withdrawal amount must be greater than zero.")

            current_balance = float(account[2])
            if amount > current_balance:
                raise ValueError("Insufficient balance!")

            new_balance = current_balance - amount

            self.cursor.execute("UPDATE accounts SET balance = %s WHERE account_number = %s", (new_balance, acc_no))
            self.cursor.execute(
                "INSERT INTO transactions (account_number, transaction_type, amount, balance) VALUES (%s, %s, %s, %s)",
                (acc_no, "Withdrawal", amount, new_balance)
            )
            self.conn.commit()
            print(f"\nSuccessfully withdrew ${amount:.2f}. New Balance: ${new_balance:.2f}")
        except ValueError as ve:
            print(f"Invalid Input: {ve}")
        except Error as e:
            self.conn.rollback()
            print(f"Database Error: {e}")

    def calculate_interest(self):
        try:
            acc_no = int(input("Enter Account Number: "))
            account = self.get_account(acc_no)
            if not account:
                print("Account not found.")
                return

            rate = float(input("Enter annual interest rate (in %): "))
            time_years = float(input("Enter time period (in years): "))
            
            if rate < 0 or time_years < 0:
                raise ValueError("Rate and time cannot be negative.")

            principal = float(account[2])
            interest = (principal * rate * time_years) / 100
            new_balance = principal + interest

            self.cursor.execute("UPDATE accounts SET balance = %s WHERE account_number = %s", (new_balance, acc_no))
            self.cursor.execute(
                "INSERT INTO transactions (account_number, transaction_type, amount, balance) VALUES (%s, %s, %s, %s)",
                (acc_no, "Simple Interest Credited", interest, new_balance)
            )
            self.conn.commit()
            print(f"\nSimple Interest of ${interest:.2f} credited. New Balance: ${new_balance:.2f}")
        except ValueError as ve:
            print(f"Invalid Input: {ve}")
        except Error as e:
            self.conn.rollback()
            print(f"Database Error: {e}")

    def view_transactions(self):
        try:
            acc_no = int(input("Enter Account Number: "))
            account = self.get_account(acc_no)
            if not account:
                print("Account not found.")
                return

            self.cursor.execute(
                "SELECT transaction_id, transaction_type, amount, transaction_date, balance FROM transactions WHERE account_number = %s ORDER BY transaction_date DESC",
                (acc_no,)
            )
            records = self.cursor.fetchall()
            print(f"\n--- Transaction History for Account #{acc_no} ({account[1]}) ---")
            print(f"{'ID':<5} | {'Type':<30} | {'Amount':<10} | {'Date & Time':<20} | {'Balance':<10}")
            print("-" * 85)
            for row in records:
                print(f"{row[0]:<5} | {row[1]:<30} | ${row[2]:<9.2f} | {str(row[3]):<20} | ${row[4]:<9.2f}")
        except ValueError:
            print("Please enter a valid account number.")
        except Error as e:
            print(f"Database Error: {e}")

    def run(self):
        """Menu-driven application loop."""
        while True:
            print("\n========================================")
            print("       BANK MANAGEMENT SYSTEM (PDBC)    ")
            print("========================================")
            print("1. Create Bank Account")
            print("2. Check Balance")
            print("3. Deposit Money")
            print("4. Withdraw Money")
            print("5. Calculate & Credit Simple Interest")
            print("6. View Transaction History")
            print("7. Exit")
            
            choice = input("Enter your choice (1-7): ").strip()
            
            if choice == '1':
                self.create_account()
            elif choice == '2':
                self.check_balance()
            elif choice == '3':
                self.deposit()
            elif choice == '4':
                self.withdraw()
            elif choice == '5':
                self.calculate_interest()
            elif choice == '6':
                self.view_transactions()
            elif choice == '7':
                print("Exiting application. Goodbye!")
                self.cursor.close()
                self.conn.close()
                break
            else:
                print("Invalid choice! Please select a number between 1 and 7.")

if __name__ == "__main__":
    app = BankManagementSystem()
    app.run()
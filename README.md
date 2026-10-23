# 🏦 Bank Management System (Python & MySQL)

A robust, menu-driven **Bank Management System** built using **Python Object-Oriented Programming (OOP)**, **Exception Handling**, and **MySQL Database Connectivity (PDBC)**. This project serves as a complete banking simulation that securely manages customer accounts, transactions, and simple interest calculations.

---

## ✨ Features

1. **Account Creation:** Open a new bank account with a customer name and initial deposit (auto-generates a unique account number).
2. **Balance Inquiry:** Check the real-time live balance of any active account.
3. **Deposit Funds:** Securely deposit money into an existing account with instant balance updates.
4. **Withdrawal Processing:** Withdraw money with built-in validation to prevent overdrafts and negative amounts.
5. **Interest Calculation:** Calculate and credit simple interest based on custom annual rates and time periods.
6. **Transaction Auditing:** Automatically record every financial action with precise timestamps.
7. **Transaction History:** View complete, sorted audit logs showing transaction types, amounts, dates, and resulting balances.
8. **Robust Error Handling:** Comprehensive `try-except` blocks to handle invalid inputs, missing accounts, and database errors gracefully.

---

## 🛠️ Technical Requirements

* **Language:** Python 3.x
* **Database:** MySQL Server & MySQL Workbench
* **Python Package:** `mysql-connector-python`
* **Concepts Applied:** 
  * Object-Oriented Programming (Classes, Objects, Constructors, Encapsulation)
  * Database Transactions (`commit()` and `rollback()`)
  * Exception Handling (`ValueError`, `mysql.connector.Error`)

---

## 📂 Database Schema

The application automatically creates a database named `bank_db` containing two relational tables:

### 1. `accounts` Table
| Column Name | Data Type | Constraints |
| :--- | :--- | :--- |
| `account_number` | INT | Primary Key, Auto Increment |
| `customer_name` | VARCHAR(100) | Not Null |
| `balance` | DECIMAL(10, 2) | Not Null |

### 2. `transactions` Table
| Column Name | Data Type | Constraints |
| :--- | :--- | :--- |
| `transaction_id` | INT | Primary Key, Auto Increment |
| `account_number` | INT | Foreign Key (`accounts.account_number`) |
| `transaction_type` | VARCHAR(50) | Description of action |
| `amount` | DECIMAL(10, 2) | Monetary value |
| `transaction_date`| TIMESTAMP | Default Current Timestamp |
| `balance` | DECIMAL(10, 2) | Balance after transaction |

---

## 🚀 Getting Started & Installation

### Prerequisites
Make sure you have Python and MySQL installed on your local machine.

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/your-username/bank-management-system.git](https://github.com/your-username/bank-management-system.git)
   cd bank-management-system

Install Required Python Dependencies:

Bash
pip install mysql-connector-python
Configure Database Credentials:
Open bank_project.py and update your local MySQL username and password in the connection string:

Python
self.conn = mysql.connector.connect(
    host="localhost",
    user="root",          # Replace with your MySQL username
    password="your_password" # Replace with your MySQL password
)
💻 How to Run
Run the script from your terminal or command prompt:

Bash
python bank_project.py
Menu Options:
Plaintext
========================================
       BANK MANAGEMENT SYSTEM (PDBC)    
========================================
1. Create Bank Account
2. Check Balance
3. Deposit Money
4. Withdraw Money
5. Calculate & Credit Simple Interest
6. View Transaction History
7. Exit
👨‍💻 Author
Mangineni Jagadeesh (Batch: D17R)

Instructor: Aparna Trainer


---

### How to use this:
1. Create a file named `README.md` in your project folder.
2. Paste the text above into it.
3. Commit and push it to your GitHub repository!

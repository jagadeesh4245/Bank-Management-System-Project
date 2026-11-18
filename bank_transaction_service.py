using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Odbc;

namespace BankTransactionService
{
    // ==========================================
    // 1. CUSTOM EXCEPTIONS
    // ==========================================

    public class InsufficientFundsException : Exception
    {
        public InsufficientFundsException(string message) : base(message) { }
    }

    public class DatabaseOperationException : Exception
    {
        public DatabaseOperationException(string message, Exception innerException)
            : base(message, innerException) { }
    }

    public class InvalidTransactionException : Exception
    {
        public InvalidTransactionException(string message) : base(message) { }
    }

    // ==========================================
    // 2. TRANSACTION TYPE ENUM
    // ==========================================

    public enum TransactionType
    {
        Deposit,
        Withdrawal,
        Transfer
    }

    // ==========================================
    // 3. DOMAIN MODEL: TRANSACTION & ACCOUNT
    // ==========================================

    public class Transaction
    {
        public Guid Id { get; set; }
        public string AccountId { get; set; }
        public decimal Amount { get; set; }
        public TransactionType Type { get; set; }
        public DateTime Timestamp { get; set; }
        public string TargetAccountId { get; set; }

        public Transaction(string accountId, decimal amount, TransactionType type, string targetAccountId = null)
        {
            Id = Guid.NewGuid();
            AccountId = accountId;
            Amount = amount;
            Type = type;
            Timestamp = DateTime.Now;
            TargetAccountId = targetAccountId;
        }

        public override string ToString()
        {
            return $"Transaction ID: {Id}, Account: {AccountId}, Amount: {Amount:C}, Type: {Type}, Time: {Timestamp}";
        }
    }

    public class Account
    {
        public string AccountId { get; set; }
        public decimal Balance { get; private set; }

        public Account(string accountId, decimal balance = 0.00m)
        {
            if (balance < 0)
            {
                throw new InvalidTransactionException("Opening balance cannot be negative.");
            }

            AccountId = accountId;
            Balance = balance;
        }

        public void ApplyTransaction(Transaction tx)
        {
            if (tx.AccountId != AccountId)
            {
                throw new InvalidTransactionException("Transaction account does not match.");
            }

            if (tx.Amount <= 0)
            {
                throw new InvalidTransactionException("Transaction amount must be positive.");
            }

            switch (tx.Type)
            {
                case TransactionType.Deposit:
                    Balance += tx.Amount;
                    break;

                case TransactionType.Withdrawal:
                case TransactionType.Transfer:
                    if (Balance < tx.Amount)
                    {
                        throw new InsufficientFundsException("Insufficient balance.");
                    }
                    Balance -= tx.Amount;
                    break;

                default:
                    throw new InvalidTransactionException("Unsupported transaction type.");
            }
        }
    }

    // ==========================================
    // 4. DATA ACCESS LAYER: DB CONNECTOR
    // ==========================================

    public class DbConnector : IDisposable
    {
        private readonly string _connectionString;
        private OdbcConnection _connection;

        public DbConnector(string connectionString)
        {
            _connectionString = connectionString;
            _connection = new OdbcConnection(_connectionString);
        }

        public void Open()
        {
            try
            {
                if (_connection == null)
                {
                    _connection = new OdbcConnection(_connectionString);
                }

                if (_connection.State != ConnectionState.Open)
                {
                    _connection.Open();
                }
            }
            catch (OdbcException ex)
            {
                throw new DatabaseOperationException($"Database connection failed: {ex.Message}", ex);
            }
        }

        public void Close()
        {
            if (_connection != null && _connection.State == ConnectionState.Open)
            {
                _connection.Close();
            }
        }

        public int ExecuteNonQuery(string sql, params OdbcParameter[] parameters)
        {
            try
            {
                Open();
                using (var command = new OdbcCommand(sql, _connection))
                {
                    if (parameters != null && parameters.Length > 0)
                    {
                        command.Parameters.AddRange(parameters);
                    }

                    return command.ExecuteNonQuery();
                }
            }
            catch (OdbcException ex)
            {
                throw new DatabaseOperationException($"Database operation failed: {ex.Message}", ex);
            }
            finally
            {
                Close();
            }
        }

        public List<Transaction> ExecuteQuery(string sql, params OdbcParameter[] parameters)
        {
            var results = new List<Transaction>();

            try
            {
                Open();
                using (var command = new OdbcCommand(sql, _connection))
                {
                    if (parameters != null && parameters.Length > 0)
                    {
                        command.Parameters.AddRange(parameters);
                    }

                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            var tx = new Transaction(
                                accountId: reader["AccountId"].ToString(),
                                amount: Convert.ToDecimal(reader["Amount"]),
                                type: (TransactionType)Enum.Parse(typeof(TransactionType), reader["Type"].ToString()),
                                targetAccountId: reader["TargetAccountId"] == DBNull.Value ? null : reader["TargetAccountId"].ToString()
                            )
                            {
                                Id = Guid.Parse(reader["Id"].ToString()),
                                Timestamp = Convert.ToDateTime(reader["Timestamp"])
                            };

                            results.Add(tx);
                        }
                    }
                }

                return results;
            }
            catch (OdbcException ex)
            {
                throw new DatabaseOperationException($"Database query failed: {ex.Message}", ex);
            }
            finally
            {
                Close();
            }
        }

        public void Dispose()
        {
            if (_connection != null)
            {
                _connection.Dispose();
                _connection = null;
            }
        }
    }

    // ==========================================
    // 5. REPOSITORY LAYER
    // ==========================================

    public class TransactionRepository
    {
        private readonly DbConnector _db;

        public TransactionRepository(DbConnector dbConnector)
        {
            _db = dbConnector;
        }

        public void Save(Transaction tx)
        {
            string sql = @"
                INSERT INTO Transactions
                (Id, AccountId, Amount, Type, Timestamp, TargetAccountId)
                VALUES (?, ?, ?, ?, ?, ?)";

            _db.ExecuteNonQuery(
                sql,
                new OdbcParameter("@Id", tx.Id.ToString()),
                new OdbcParameter("@AccountId", tx.AccountId),
                new OdbcParameter("@Amount", tx.Amount),
                new OdbcParameter("@Type", tx.Type.ToString()),
                new OdbcParameter("@Timestamp", tx.Timestamp),
                new OdbcParameter("@TargetAccountId", (object)tx.TargetAccountId ?? DBNull.Value)
            );
        }

        public List<Transaction> GetByAccount(string accountId)
        {
            string sql = @"
                SELECT Id, AccountId, Amount, Type, Timestamp, TargetAccountId
                FROM Transactions
                WHERE AccountId = ?
                ORDER BY Timestamp DESC";

            return _db.ExecuteQuery(sql, new OdbcParameter("@AccountId", accountId));
        }
    }

    // ==========================================
    // 6. SERVICE LAYER: BANK SERVICE
    // ==========================================

    public class BankService
    {
        private readonly Account _account;
        private readonly TransactionRepository _repository;

        public BankService(Account account, TransactionRepository repository)
        {
            _account = account;
            _repository = repository;
        }

        private Transaction ProcessTransaction(decimal amount, TransactionType type, string targetAccountId = null)
        {
            // Validate business rules before database access
            if (amount <= 0)
            {
                throw new InvalidTransactionException("Amount must be a positive number.");
            }

            if ((type == TransactionType.Withdrawal || type == TransactionType.Transfer) && _account.Balance < amount)
            {
                throw new InsufficientFundsException("Insufficient funds for this transaction.");
            }

            var tx = new Transaction(_account.AccountId, amount, type, targetAccountId);

            // Persist first so a DB error prevents updating in-memory balance
            _repository.Save(tx);

            // Update account balance after save succeeds
            _account.ApplyTransaction(tx);

            return tx;
        }

        public Transaction Deposit(decimal amount)
        {
            var tx = ProcessTransaction(amount, TransactionType.Deposit);
            Console.WriteLine("Deposit successful.");
            return tx;
        }

        public Transaction Withdraw(decimal amount)
        {
            var tx = ProcessTransaction(amount, TransactionType.Withdrawal);
            Console.WriteLine("Withdrawal successful.");
            return tx;
        }

        public Transaction Transfer(string targetAccountId, decimal amount)
        {
            if (string.IsNullOrWhiteSpace(targetAccountId))
            {
                throw new InvalidTransactionException("Target account ID cannot be empty.");
            }

            if (targetAccountId == _account.AccountId)
            {
                throw new InvalidTransactionException("Cannot transfer to the same account.");
            }

            var tx = ProcessTransaction(amount, TransactionType.Transfer, targetAccountId);
            Console.WriteLine("Transfer recorded successfully.");
            return tx;
        }
    }
}
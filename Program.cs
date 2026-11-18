using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Odbc;
using System.IO;

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
        public string? TargetAccountId { get; set; }

        public Transaction(string accountId, decimal amount, TransactionType type, string? targetAccountId = null)
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
        private readonly OdbcConnection _connection;

        public DbConnector(string connectionString)
        {
            _connectionString = connectionString;
            _connection = new OdbcConnection(_connectionString);
        }

        public void Open()
        {
            try
            {
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
            if (_connection.State == ConnectionState.Open)
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
                        int idOrdinal = reader.GetOrdinal("Id");
                        int accountIdOrdinal = reader.GetOrdinal("AccountId");
                        int amountOrdinal = reader.GetOrdinal("Amount");
                        int typeOrdinal = reader.GetOrdinal("Type");
                        int timestampOrdinal = reader.GetOrdinal("Timestamp");
                        int targetAccountIdOrdinal = reader.GetOrdinal("TargetAccountId");

                        while (reader.Read())
                        {
                            if (reader.IsDBNull(accountIdOrdinal))
                            {
                                throw new InvalidDataException("Transaction AccountId cannot be null.");
                            }

                            if (reader.IsDBNull(typeOrdinal)
                                || !Enum.TryParse(
                                    Convert.ToString(reader.GetValue(typeOrdinal)),
                                    out TransactionType transactionType))
                            {
                                throw new InvalidDataException("Transaction Type is missing or invalid.");
                            }

                            if (reader.IsDBNull(idOrdinal)
                                || !Guid.TryParse(Convert.ToString(reader.GetValue(idOrdinal)), out Guid id))
                            {
                                throw new InvalidDataException("Transaction Id is missing or invalid.");
                            }

                            if (reader.IsDBNull(timestampOrdinal))
                            {
                                throw new InvalidDataException("Transaction Timestamp cannot be null.");
                            }

                            string? targetAccountId = reader.IsDBNull(targetAccountIdOrdinal)
                                ? null
                                : reader.GetString(targetAccountIdOrdinal);

                            var tx = new Transaction(
                                accountId: reader.GetString(accountIdOrdinal),
                                amount: Convert.ToDecimal(reader.GetValue(amountOrdinal)),
                                type: transactionType,
                                targetAccountId: targetAccountId
                            )
                            {
                                Id = id,
                                Timestamp = Convert.ToDateTime(reader.GetValue(timestampOrdinal))
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
            _connection.Dispose();
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
                (Id, AccountId, Amount, [Type], [Timestamp], TargetAccountId)
                VALUES (?, ?, ?, ?, ?, ?)";
            object targetAccountParameter = tx.TargetAccountId is null
                ? DBNull.Value
                : tx.TargetAccountId;

            _db.ExecuteNonQuery(
                sql,
                new OdbcParameter("@Id", tx.Id.ToString()),
                new OdbcParameter("@AccountId", tx.AccountId),
                new OdbcParameter("@Amount", tx.Amount),
                new OdbcParameter("@Type", tx.Type.ToString()),
                new OdbcParameter("@Timestamp", OdbcType.DateTime)
                {
                    Scale = 7,
                    Value = tx.Timestamp
                },
                new OdbcParameter("@TargetAccountId", targetAccountParameter)
            );
        }

        public List<Transaction> GetByAccount(string accountId)
        {
            string sql = @"
                SELECT Id, AccountId, Amount, [Type], [Timestamp], TargetAccountId
                FROM Transactions
                WHERE AccountId = ?
                ORDER BY [Timestamp] DESC";

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

        private Transaction ProcessTransaction(decimal amount, TransactionType type, string? targetAccountId = null)
        {
            if (amount <= 0)
            {
                throw new InvalidTransactionException("Amount must be a positive number.");
            }

            if ((type == TransactionType.Withdrawal || type == TransactionType.Transfer) && _account.Balance < amount)
            {
                throw new InsufficientFundsException("Insufficient funds for this transaction.");
            }

            var tx = new Transaction(_account.AccountId, amount, type, targetAccountId);

            // Persist transaction via repository
            _repository.Save(tx);

            // Update account balance using Account.ApplyTransaction
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

    // ==========================================
    // 7. UNIT TEST STUBS (Task 6)
    // ==========================================

    public class BankServiceTestStubs
    {
        // Verifies Deposit increases account balance and saves a Deposit transaction.
        public void Deposit_ValidAmount_IncreasesBalanceAndSavesTransaction() { }

        // Verifies Deposit throws InvalidTransactionException when amount <= 0 before DB access.
        public void Deposit_NonPositiveAmount_ThrowsInvalidTransactionException() { }

        // Verifies Withdraw decreases account balance and saves a Withdrawal transaction.
        public void Withdraw_ValidAmount_DecreasesBalanceAndSavesTransaction() { }

        // Verifies Withdraw throws InsufficientFundsException when balance is lower than withdrawal amount.
        public void Withdraw_InsufficientBalance_ThrowsInsufficientFundsException() { }

        // Verifies Transfer decreases source account balance and saves a Transfer transaction with TargetAccountId.
        public void Transfer_ValidTargetAndAmount_UpdatesBalanceAndSavesTransaction() { }

        // Verifies Transfer throws InvalidTransactionException when targetAccountId is null, empty, or same as source.
        public void Transfer_InvalidTargetAccount_ThrowsInvalidTransactionException() { }

        // Verifies database failures wrap OdbcException in DatabaseOperationException preserving original message.
        public void ServiceOperation_DatabaseFailure_ThrowsDatabaseOperationException() { }
    }

    // ==========================================
    // 8. MAIN PROGRAM EXECUTION
    // ==========================================

    class Program
    {
        static void Main(string[] args)
        {
            string connectionString =
                "Driver={ODBC Driver 18 for SQL Server};" +
                "Server=localhost\\SQLEXPRESS;" +
                "Database=BankDB;" +
                "Trusted_Connection=yes;" +
                "TrustServerCertificate=yes;";

            using (var db = new DbConnector(connectionString))
            {
                var repository = new TransactionRepository(db);
                var account = new Account("ACC1001", 5000.00m);
                var bank = new BankService(account, repository);

                try
                {
                    Console.WriteLine($"Initial balance: {account.Balance:C}");
                    bank.Deposit(1000.00m);
                    bank.Withdraw(500.00m);
                    bank.Transfer("ACC1002", 300.00m);
                    Console.WriteLine($"Final balance: {account.Balance:C}");

                    Console.WriteLine("\nTransaction History:");
                    foreach (var tx in repository.GetByAccount("ACC1001"))
                    {
                        Console.WriteLine(tx);
                    }
                }
                catch (InvalidTransactionException ex)
                {
                    Console.WriteLine($"Invalid transaction: {ex.Message}");
                }
                catch (InsufficientFundsException ex)
                {
                    Console.WriteLine($"Insufficient funds: {ex.Message}");
                }
                catch (DatabaseOperationException ex)
                {
                    Console.WriteLine($"Database error: {ex.Message}");
                }
            }
        }
    }
}
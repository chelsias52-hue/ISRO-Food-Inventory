"""Add the inventory schema's query indexes and CHECK constraints in place."""

import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

load_dotenv()

INDEXES = (
    (
        "food_items",
        "idx_food_items_expiry_date",
        "CREATE INDEX idx_food_items_expiry_date ON food_items (expiry_date)",
    ),
    (
        "missions",
        "idx_missions_status_launch_date",
        "CREATE INDEX idx_missions_status_launch_date ON missions (status, launch_date)",
    ),
    (
        "food_allocation",
        "idx_food_allocation_date",
        "CREATE INDEX idx_food_allocation_date ON food_allocation (allocation_date)",
    ),
    (
        "stock_transactions",
        "idx_stock_transactions_date_type",
        "CREATE INDEX idx_stock_transactions_date_type "
        "ON stock_transactions (transaction_date, transaction_type)",
    ),
)

CHECKS = (
    (
        "inventory",
        "chk_inventory_quantity_nonnegative",
        "SELECT COUNT(*) FROM inventory WHERE quantity < 0",
        "ALTER TABLE inventory ADD CONSTRAINT chk_inventory_quantity_nonnegative "
        "CHECK (quantity >= 0)",
    ),
    (
        "inventory",
        "chk_inventory_reorder_nonnegative",
        "SELECT COUNT(*) FROM inventory WHERE reorder_level < 0",
        "ALTER TABLE inventory ADD CONSTRAINT chk_inventory_reorder_nonnegative "
        "CHECK (reorder_level >= 0)",
    ),
    (
        "missions",
        "chk_missions_duration_positive",
        "SELECT COUNT(*) FROM missions WHERE duration_days <= 0",
        "ALTER TABLE missions ADD CONSTRAINT chk_missions_duration_positive "
        "CHECK (duration_days IS NULL OR duration_days > 0)",
    ),
    (
        "missions",
        "chk_missions_crew_positive",
        "SELECT COUNT(*) FROM missions WHERE crew_size <= 0",
        "ALTER TABLE missions ADD CONSTRAINT chk_missions_crew_positive "
        "CHECK (crew_size IS NULL OR crew_size > 0)",
    ),
    (
        "food_allocation",
        "chk_food_allocation_quantity_positive",
        "SELECT COUNT(*) FROM food_allocation WHERE quantity <= 0",
        "ALTER TABLE food_allocation ADD CONSTRAINT "
        "chk_food_allocation_quantity_positive CHECK (quantity > 0)",
    ),
    (
        "stock_transactions",
        "chk_stock_transaction_quantity_positive",
        "SELECT COUNT(*) FROM stock_transactions WHERE quantity <= 0",
        "ALTER TABLE stock_transactions ADD CONSTRAINT "
        "chk_stock_transaction_quantity_positive CHECK (quantity > 0)",
    ),
)


def main():
    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        raise RuntimeError("Set MYSQL_PASSWORD before running this migration.")

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "root"),
            password=password,
            database=os.environ.get("MYSQL_DATABASE", "nasa_food_inventory"),
        )
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
        )
        existing_tables = {row[0] for row in cursor.fetchall()}
        required_tables = {table for table, _, _ in INDEXES} | {
            table for table, _, _, _ in CHECKS
        }
        missing_tables = required_tables - existing_tables
        if missing_tables:
            raise RuntimeError(
                "Missing expected tables: " + ", ".join(sorted(missing_tables))
            )

        for table, name, query, _ in CHECKS:
            cursor.execute(query)
            invalid_count = cursor.fetchone()[0]
            if invalid_count:
                raise RuntimeError(
                    f"Cannot add {name}: {invalid_count} existing row(s) violate it."
                )

        for table, name, statement in INDEXES:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = %s
                  AND index_name = %s
                """,
                (table, name),
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(statement)
                print(f"Added index {table}.{name}.")
            else:
                print(f"Index {table}.{name} already exists.")

        for table, name, _, statement in CHECKS:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_schema = DATABASE()
                  AND table_name = %s
                  AND constraint_name = %s
                  AND constraint_type = 'CHECK'
                """,
                (table, name),
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(statement)
                print(f"Added check constraint {table}.{name}.")
            else:
                print(f"Check constraint {table}.{name} already exists.")
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()

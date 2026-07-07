import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_mock_database():
    """Simulates a corporate database with raw transactional records."""
    print("⏳ Creating mock database and generating raw transaction logs...")
    conn = sqlite3.connect("corporate_sales.db")
    cursor = conn.cursor()
    
    # Create Raw Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            store_id INTEGER,
            product_id INTEGER,
            units_sold INTEGER,
            unit_price REAL,
            is_promo INTEGER
        )
    """)

    # Create Product Metadata Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_metadata (
            product_id INTEGER PRIMARY KEY,
            category TEXT,
            brand TEXT
        )
    """)

    cursor.execute("DELETE FROM raw_transactions")
    cursor.execute("DELETE FROM product_metadata")

    # Generate Synthetic Data (5 Stores, 6 Products, 180 Days)
    np.random.seed(42)
    start_date = datetime(2026, 1, 1)

    # Insert metadata with multiple categories and products
    products = [
        (101, 'Electronics', 'TechCorp'),
        (102, 'Groceries', 'FreshFarm'),
        (103, 'Apparel & Textiles', 'StyleHub'),
        (104, 'Home Goods', 'HomeNest'),
        (105, 'Electronics', 'GadgetCo'),
        (106, 'Groceries', 'MarketPlus')
    ]
    cursor.executemany("INSERT OR REPLACE INTO product_metadata VALUES (?, ?, ?)", products)

    transactions = []
    for day in range(180):
        current_date = (start_date + timedelta(days=day)).strftime('%Y-%m-%d')
        for store in range(1, 6):
            for prod_id, cat, brand in products:
                is_promo = 1 if np.random.rand() > 0.85 else 0
                base_sales = 50 if prod_id in {101, 105} else 120 if prod_id in {102, 106} else 80 if prod_id == 103 else 70
                day_of_week = (start_date + timedelta(days=day)).weekday()
                weekend_boost = 20 if day_of_week >= 5 else 0
                promo_boost = np.random.randint(30, 70) if is_promo else 0

                units = int(base_sales + weekend_boost + promo_boost + np.random.normal(0, 10))
                units = max(0, units)
                price = 299.99 if prod_id in {101, 105} else 4.99 if prod_id in {102, 106} else 59.99 if prod_id == 103 else 89.99

                transactions.append((current_date, store, prod_id, units, price, is_promo))

    cursor.executemany("""
        INSERT INTO raw_transactions (date, store_id, product_id, units_sold, unit_price, is_promo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, transactions)
    
    conn.commit()
    print("✅ Database successfully created and populated!")
    return conn

def run_advanced_feature_pipeline(conn):
    """
    Executes a production-grade SQL script using CTEs and Window Functions
    to build time-series lag and rolling statistics features.
    """
    print("⏳ Running Advanced SQL Feature Engineering Pipeline...")
    
    sql_query = """
    WITH BaseData AS (
        -- Step 1: Clean and join raw transactions with product metadata
        SELECT 
            t.date,
            t.store_id,
            t.product_id,
            m.category,
            t.units_sold,
            t.unit_price,
            t.is_promo
        FROM raw_transactions t
        JOIN product_metadata m ON t.product_id = m.product_id
    ),
    TimeFeatures AS (
        -- Step 2: Use Window Functions to calculate historical lags and moving averages
        SELECT 
            date,
            store_id,
            product_id,
            category,
            units_sold,
            unit_price,
            is_promo,
            
            -- Lag Features: What did we sell 1 day ago and 7 days ago?
            LAG(units_sold, 1) OVER (PARTITION BY store_id, product_id ORDER BY date) AS lag_1,
            LAG(units_sold, 7) OVER (PARTITION BY store_id, product_id ORDER BY date) AS lag_7,
            
            -- Rolling Window Features: 7-day moving average sales
            AVG(units_sold) OVER (
                PARTITION BY store_id, product_id 
                ORDER BY date 
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) AS rolling_avg_7,
            
            -- Rolling Window Features: 30-day moving average sales
            AVG(units_sold) OVER (
                PARTITION BY store_id, product_id 
                ORDER BY date 
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) AS rolling_avg_30
            
        FROM BaseData
    )
    -- Step 3: Filter out initial rows that don't have enough history for lags
    SELECT * FROM TimeFeatures 
    WHERE lag_7 IS NOT NULL AND rolling_avg_30 IS NOT NULL
    ORDER BY store_id, product_id, date;
    """
    
    df_features = pd.read_sql_query(sql_query, conn)
    df_features.to_csv("engineered_features.csv", index=False)
    print("✅ Data layer pipeline complete! Features saved to 'engineered_features.csv'.")
    print(f"📊 Extracted Data Shape: {df_features.shape}")
    print(df_features.head(3))

if __name__ == "__main__":
    db_connection = create_mock_database()
    run_advanced_feature_pipeline(db_connection)
    db_connection.close()
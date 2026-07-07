import sqlite3

# Connect to your local database file
conn = sqlite3.connect("corporate_sales.db")
cursor = conn.cursor()

print("Inserting new simulated distribution hubs...")

# Insert mock records for new hubs so the code has data to read
# Format: (date, store_id, product_id, units_sold, unit_price, is_promo)
new_data = [
    ('2026-07-01', 3, 101, 45, 49.99, 0),
    ('2026-07-01', 4, 102, 60, 29.99, 1),
    ('2026-07-01', 5, 105, 30, 99.99, 0)
]

cursor.executemany("""
    INSERT INTO raw_transactions (date, store_id, product_id, units_sold, unit_price, is_promo)
    VALUES (?, ?, ?, ?, ?, ?);
""", new_data)

conn.commit()
conn.close()
print("✅ Done! Hub 3, Hub 4, and Hub 5 have been injected into the database layer.")
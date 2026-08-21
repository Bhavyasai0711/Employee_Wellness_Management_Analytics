import sqlite3

conn = sqlite3.connect("instance/employee_wellness.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN profile_image VARCHAR(200) DEFAULT 'default.png';
    """)
    conn.commit()
    print("✅ profile_image column added successfully!")
except Exception as e:
    print("❌ Error:", e)

conn.close()
import pymysql

try:
    conn = pymysql.connect(
        host="localhost",
        user="alphaess",
        password="alphaess123",
        db="alphaess",
        charset="utf8mb4",
    )
    print("✅ Verbindung OK")
    conn.close()
except Exception as e:
    print(f"❌ Fehler: {e}")


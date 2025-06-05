import sqlite3
import pandas as pd
import os

# 연결
conn = sqlite3.connect('memory_app.db')

# 테이블별 데이터 확인
print("=== USERS ===")
print(pd.read_sql_query("SELECT * FROM USERS", conn))

print("\n=== USER_ANSWERS ===") 
print(pd.read_sql_query("SELECT * FROM USER_ANSWERS", conn))

conn.close()
import sqlite3

DATABASE_FILE = "resume_ranker.db"
TABLE_TO_CLEAR = "resumes"

try:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute(f"DELETE FROM {TABLE_TO_CLEAR}")
    conn.commit()
    conn.close()
    print(f"Table '{TABLE_TO_CLEAR}' has been cleared.")
except Exception as e:
    print(f"An error occurred: {e}")

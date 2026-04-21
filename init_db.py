import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

def init_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)

    conn.autocommit = True
    
    with open('schema.sql', 'r') as f:
        schema = f.read()
    
    cur = conn.cursor()
    cur.execute(schema)
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()

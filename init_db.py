import psycopg2

def init_database():
    conn = psycopg2.connect(
        dbname="school_scrapper_db",
        user="postgres",
        password="Infinity",
        host="localhost"
    )
    conn.autocommit = True
    
    with open('schema.sql', 'r') as f:
        schema = f.read()
    
    cur = conn.cursor()
    cur.execute(schema)
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()

import os
import psycopg2
from config.configs import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB

def check_db():
    try:
        with open("db_debug.log", "w") as f:
            f.write(f"Connecting to host={POSTGRES_HOST}, port={POSTGRES_PORT}, user={POSTGRES_USER}...\n")
            # Try connecting to 'postgres' database first to verify credentials
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                dbname="postgres"
            )
            f.write("Successfully connected to 'postgres' database (Authentication OK).\n")
            
            # Check if the target database exists
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{POSTGRES_DB}'")
            exists = cur.fetchone()
            
            if exists:
                f.write(f"Database '{POSTGRES_DB}' exists.\n")
            else:
                f.write(f"Database '{POSTGRES_DB}' does NOT exist. Attempting to create it...\n")
                try:
                    cur.execute(f"CREATE DATABASE {POSTGRES_DB}")
                    f.write(f"Database '{POSTGRES_DB}' created successfully.\n")
                except Exception as e:
                    f.write(f"Failed to create database '{POSTGRES_DB}': {e}\n")
            
            cur.close()
            conn.close()
            print("Done. Check db_debug.log")
    except Exception as e:
        with open("db_debug.log", "a") as f:
            f.write(f"Authentication failed or server unreachable: {e}\n")
        print(f"Error: {e}. Check db_debug.log")

if __name__ == "__main__":
    check_db()

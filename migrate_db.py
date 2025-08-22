#!/usr/bin/env python3
"""
Database migration script to add missing updated_at column
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "chatbotdb")
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def migrate_database():
    """Add missing updated_at column to chat_sessions table"""
    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chat_sessions' 
                AND column_name = 'updated_at'
            """))

            if result.fetchone():
                print("✅ Column 'updated_at' already exists!")
                return

            # Add the missing column
            print("🔧 Adding 'updated_at' column to chat_sessions table...")
            conn.execute(text("""
                ALTER TABLE chat_sessions 
                ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()
            """))

            # Update existing records
            print("📝 Updating existing records...")
            conn.execute(text("""
                UPDATE chat_sessions 
                SET updated_at = created_at 
                WHERE updated_at IS NULL
            """))

            conn.commit()
            print("✅ Database migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)

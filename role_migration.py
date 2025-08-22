#!/usr/bin/env python3
"""
Role-based auth migration script with doctor verification
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Use environment variable or default
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "chatbotdb")
    DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = create_engine(DB_URL)

def main():
    print("🏥 Medical RAG Chatbot - Role-Based Authentication Migration")
    print("=" * 60)
    success = False
    try:
        with engine.connect() as conn:
            print("🔍 Running role-based authentication migration...")
            # Your migration steps here
            # e.g., adding columns, creating tables, inserting data
            # For example:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'general'"))
            except Exception as e:
                if "already exists" in str(e):
                    print("⚠️ 'role' column already exists, continuing...")
                else:
                    raise

            # Create doctors_registry table
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS doctors_registry (
                        id SERIAL PRIMARY KEY,
                        legal_no VARCHAR(50) UNIQUE NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        phone_number VARCHAR(20) NOT NULL,
                        specialization VARCHAR(255),
                        license_status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            except Exception as e:
                print(f"Error creating table: {e}")

            # Insert sample data
            try:
                conn.execute(text("""
                    INSERT INTO doctors_registry (legal_no, full_name, phone_number, specialization) 
                    VALUES 
                        ('MED001', 'Dr. Rajesh Kumar', '9876543210', 'General Medicine'),
                        ('MED002', 'Dr. Priya Sharma', '8765432109', 'Cardiology'),
                        ('MED003', 'Dr. Amit Patel', '7654321098', 'Orthopedics'),
                        ('MED004', 'Dr. Sunita Reddy', '6543210987', 'Pediatrics'),
                        ('MED005', 'Dr. Vikram Singh', '5432109876', 'Neurology')
                    ON CONFLICT (legal_no) DO NOTHING
                """))
                conn.commit()
                print("✅ Sample doctor data inserted")
                success = True
            except Exception as e:
                print(f"Error inserting sample data: {e}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")

    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("Migration completed with errors or no changes.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Startup script for Medical RAG Chatbot
"""
import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import psycopg2
        import sentence_transformers
        import faiss
        import groq
        import google.generativeai
        print("✓ All required packages are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("Please install requirements with: pip install -r requirements.txt")
        return False

def check_database():
    """Check database connection"""
    try:
        from backend.db import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and database 'chatbotdb' exists")
        return False

def create_directories():
    """Create necessary directories"""
    dirs = ["data/pdfs", "data/index", "static", "templates"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    print("✓ Directories created")

def check_env_file():
    """Check if .env file exists"""
    if not Path(".env").exists():
        print("✗ .env file not found")
        print("Please create a .env file with required environment variables")
        return False
    print("✓ .env file found")
    return True

def main():
    """Main startup function"""
    print("Medical RAG Chatbot - Startup Check")
    print("=" * 40)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Check .env file
    if not check_env_file():
        sys.exit(1)

    # Create directories
    create_directories()

    # Check database
    if not check_database():
        print("\nDatabase setup instructions:")
        print("1. Start PostgreSQL service")
        print("2. Create database: createdb chatbotdb")
        print("3. Update .env file with correct database credentials")
        sys.exit(1)

    print("\n✓ All checks passed!")
    print("Starting Medical RAG Chatbot...")
    print("Access the application at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 40)

    # Start the server
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "backend.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")

if __name__ == "__main__":
    main()

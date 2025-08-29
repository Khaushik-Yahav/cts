#!/usr/bin/env python3
"""
Cleanup Script for Medical RAG Chatbot
Removes all vector database data and optionally PDF files
"""

import os
import shutil
import sys
from pathlib import Path

def cleanup_vector_database(index_dir: str = "data/index"):
    """Clean up all vector database files"""
    print("🧹 Cleaning up vector database...")
    
    if os.path.exists(index_dir):
        try:
            shutil.rmtree(index_dir)
            print(f"✅ Removed vector database directory: {index_dir}")
        except Exception as e:
            print(f"❌ Error removing vector database: {e}")
    else:
        print(f"ℹ️ Vector database directory doesn't exist: {index_dir}")
    
    # Recreate the directory structure
    os.makedirs(index_dir, exist_ok=True)
    print(f"📁 Recreated empty directory: {index_dir}")

def cleanup_uploaded_files(pdf_dir: str = "data/pdfs"):
    """Clean up all uploaded PDF and image files"""
    print("🗂️ Cleaning up uploaded files...")
    
    if not os.path.exists(pdf_dir):
        print(f"ℹ️ Upload directory doesn't exist: {pdf_dir}")
        return
    
    files_removed = 0
    for file_name in os.listdir(pdf_dir):
        file_path = os.path.join(pdf_dir, file_name)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                files_removed += 1
                print(f"🗑️ Removed: {file_name}")
            except Exception as e:
                print(f"❌ Error removing {file_name}: {e}")
    
    print(f"✅ Removed {files_removed} files from {pdf_dir}")

def cleanup_backup_directories():
    """Clean up any backup directories created during previous operations"""
    print("🔄 Cleaning up backup directories...")
    
    backup_count = 0
    for item in os.listdir("data"):
        if item.startswith("index_backup_"):
            backup_path = os.path.join("data", item)
            if os.path.isdir(backup_path):
                try:
                    shutil.rmtree(backup_path)
                    backup_count += 1
                    print(f"🗑️ Removed backup: {backup_path}")
                except Exception as e:
                    print(f"❌ Error removing backup {backup_path}: {e}")
    
    if backup_count == 0:
        print("ℹ️ No backup directories found")
    else:
        print(f"✅ Removed {backup_count} backup directories")

def show_current_status():
    """Show current status of directories and files"""
    print("\n📊 Current Status:")
    print("=" * 50)
    
    # Check vector database
    index_dir = "data/index"
    if os.path.exists(index_dir):
        index_files = os.listdir(index_dir)
        print(f"Vector DB files: {len(index_files)} files")
        for file in index_files:
            file_path = os.path.join(index_dir, file)
            size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
            print(f"  - {file}: {size} bytes")
    else:
        print("Vector DB: Directory doesn't exist")
    
    # Check uploaded files
    pdf_dir = "data/pdfs"
    if os.path.exists(pdf_dir):
        uploaded_files = [f for f in os.listdir(pdf_dir) if os.path.isfile(os.path.join(pdf_dir, f))]
        print(f"Uploaded files: {len(uploaded_files)} files")
        for file in uploaded_files:
            file_path = os.path.join(pdf_dir, file)
            size = os.path.getsize(file_path)
            print(f"  - {file}: {size} bytes")
    else:
        print("Uploaded files: Directory doesn't exist")

def main():
    """Main cleanup function"""
    print("🧽 Medical RAG Chatbot - Data Cleanup Tool")
    print("=" * 50)
    
    # Show current status
    show_current_status()
    
    print("\nChoose cleanup option:")
    print("1. Clean vector database only")
    print("2. Clean uploaded files only") 
    print("3. Clean everything (vector DB + uploaded files + backups)")
    print("4. Show status and exit")
    print("5. Exit without cleaning")
    
    try:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            cleanup_vector_database()
            
        elif choice == "2":
            cleanup_uploaded_files()
            
        elif choice == "3":
            cleanup_vector_database()
            cleanup_uploaded_files()
            cleanup_backup_directories()
            
        elif choice == "4":
            pass  # Status already shown
            
        elif choice == "5":
            print("👋 Exiting without changes")
            return
            
        else:
            print("❌ Invalid choice. Exiting.")
            return
            
        # Show final status
        print("\n" + "=" * 50)
        show_current_status()
        print("\n✅ Cleanup completed!")
        
    except KeyboardInterrupt:
        print("\n👋 Cleanup cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
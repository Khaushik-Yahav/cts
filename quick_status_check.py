#!/usr/bin/env python3
"""
Quick Status Check for Medical RAG Chatbot
Shows current status and provides troubleshooting information
"""

import os
import json
import requests
from datetime import datetime

def check_directory_structure():
    """Check if all required directories exist"""
    print("📁 Checking directory structure...")
    
    required_dirs = [
        "data",
        "data/pdfs", 
        "data/index",
        "backend",
        "static",
        "templates"
    ]
    
    missing_dirs = []
    existing_dirs = []
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            existing_dirs.append(dir_path)
        else:
            missing_dirs.append(dir_path)
    
    print(f"✅ Existing directories: {len(existing_dirs)}")
    for d in existing_dirs:
        print(f"   - {d}")
        
    if missing_dirs:
        print(f"❌ Missing directories: {len(missing_dirs)}")
        for d in missing_dirs:
            print(f"   - {d}")
    
    return len(missing_dirs) == 0

def check_uploaded_files():
    """Check what files are currently uploaded"""
    print("📄 Checking uploaded files...")
    
    pdf_dir = "data/pdfs"
    if not os.path.exists(pdf_dir):
        print("❌ Upload directory doesn't exist")
        return []
    
    files = os.listdir(pdf_dir)
    if not files:
        print("ℹ️ No files uploaded")
        return []
    
    file_info = []
    for filename in files:
        filepath = os.path.join(pdf_dir, filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            mtime = os.path.getmtime(filepath)
            modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            file_type = "Unknown"
            if filename.lower().endswith('.pdf'):
                file_type = "PDF"
            elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                file_type = "Image"
            
            file_info.append({
                "name": filename,
                "type": file_type,
                "size": size,
                "modified": modified
            })
    
    print(f"📊 Found {len(file_info)} files:")
    for info in file_info:
        print(f"   - {info['name']} ({info['type']}, {info['size']} bytes, modified: {info['modified']})")
    
    return file_info

def check_vector_database():
    """Check vector database status"""
    print("🧠 Checking vector database...")
    
    index_dir = "data/index"
    if not os.path.exists(index_dir):
        print("❌ Index directory doesn't exist")
        return False
    
    index_files = [f for f in os.listdir(index_dir) if os.path.isfile(os.path.join(index_dir, f))]
    
    if not index_files:
        print("ℹ️ No index files found")
        return False
    
    total_size = 0
    for filename in index_files:
        filepath = os.path.join(index_dir, filename)
        size = os.path.getsize(filepath)
        total_size += size
        print(f"   - {filename}: {size} bytes")
    
    print(f"📊 Total index size: {total_size} bytes")
    return True

def check_server_status():
    """Check if server is running and responsive"""
    print("🌐 Checking server status...")
    
    try:
        # Health check
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server health check passed")
        else:
            print(f"⚠️ Server health check returned: {health_response.status_code}")
            
        # Check if login works
        login_data = {
            "username": "admin", 
            "password": "admin123",
            "email": "admin@example.com"
        }
        
        login_response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=5)
        if login_response.status_code == 200:
            print("✅ Authentication working")
        else:
            print(f"⚠️ Authentication failed: {login_response.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server - is it running on port 8000?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Server timeout - may be overloaded")
        return False
    except Exception as e:
        print(f"❌ Server check error: {e}")
        return False

def quick_query_test():
    """Test a simple query"""
    print("⚡ Testing quick query...")
    
    try:
        session = requests.Session()
        
        # Login
        login_data = {
            "username": "admin",
            "password": "admin123", 
            "email": "admin@example.com"
        }
        login_response = session.post("http://localhost:8000/auth/login", json=login_data, timeout=10)
        
        if login_response.status_code != 200:
            print("❌ Login failed")
            return False
        
        # Simple test query
        test_query = "What medications are available?"
        query_response = session.post("http://localhost:8000/ask", json={"question": test_query}, timeout=15)
        
        if query_response.status_code == 200:
            result = query_response.json()
            answer = result.get('answer', '')
            sources = result.get('sources', [])
            
            print(f"✅ Query successful")
            print(f"   Answer length: {len(answer)} characters")
            print(f"   Sources found: {len(sources)}")
            
            # Check for greeting behavior
            if any(word in answer.lower() for word in ['hello', 'assistant', 'help you']):
                print("⚠️ Response contains greeting-like text")
            
            # Check source types
            pdf_sources = sum(1 for s in sources if s.get('source', '').endswith('.pdf'))
            img_sources = sum(1 for s in sources if s.get('source', '').endswith(('.png', '.jpg')))
            
            print(f"   PDF sources: {pdf_sources}")
            print(f"   Image sources: {img_sources}")
            
            return True
            
        else:
            print(f"❌ Query failed: {query_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Query test error: {e}")
        return False

def generate_status_report():
    """Generate a comprehensive status report"""
    print("📋 Generating status report...")
    print("=" * 50)
    
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "directories_ok": False,
        "files_count": 0,
        "vector_db_ok": False,
        "server_ok": False,
        "query_test_ok": False,
        "issues": []
    }
    
    # Check directories
    if not check_directory_structure():
        report["issues"].append("Missing required directories")
    else:
        report["directories_ok"] = True
    
    print()
    
    # Check files
    files = check_uploaded_files()
    report["files_count"] = len(files)
    if len(files) == 0:
        report["issues"].append("No files uploaded")
    
    print()
    
    # Check vector DB
    if not check_vector_database():
        report["issues"].append("Vector database not initialized")
    else:
        report["vector_db_ok"] = True
    
    print()
    
    # Check server
    if not check_server_status():
        report["issues"].append("Server not responding")
    else:
        report["server_ok"] = True
    
    print()
    
    # Test query
    if report["server_ok"]:
        if quick_query_test():
            report["query_test_ok"] = True
        else:
            report["issues"].append("Query processing failed")
    
    print()
    print("📊 SUMMARY REPORT")
    print("=" * 30)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Directories: {'✅' if report['directories_ok'] else '❌'}")
    print(f"Files uploaded: {report['files_count']}")
    print(f"Vector database: {'✅' if report['vector_db_ok'] else '❌'}")
    print(f"Server status: {'✅' if report['server_ok'] else '❌'}")
    print(f"Query test: {'✅' if report['query_test_ok'] else '❌'}")
    
    if report["issues"]:
        print(f"\n⚠️ Issues found ({len(report['issues'])}):")
        for issue in report["issues"]:
            print(f"   - {issue}")
    else:
        print("\n🎉 All checks passed!")
    
    return report

def main():
    """Main function"""
    print("🔍 Medical RAG Chatbot - Quick Status Check")
    print("=" * 50)
    
    print("Choose option:")
    print("1. Full status report")
    print("2. Check directories only")
    print("3. Check uploaded files only")
    print("4. Check vector database only")
    print("5. Check server only")
    print("6. Test query only")
    print("7. Exit")
    
    try:
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == "1":
            generate_status_report()
        elif choice == "2":
            check_directory_structure()
        elif choice == "3":
            check_uploaded_files()
        elif choice == "4":
            check_vector_database()
        elif choice == "5":
            check_server_status()
        elif choice == "6":
            quick_query_test()
        elif choice == "7":
            print("👋 Exiting")
            return
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
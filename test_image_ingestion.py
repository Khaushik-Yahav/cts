#!/usr/bin/env python3
"""
Fixed Testing Script for Medical RAG Chatbot Image Ingestion
Tests image processing, OCR, and retrieval functionality with proper authentication
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
import base64

def test_server_health():
    """Test if the server is running and healthy"""
    print("🏥 Testing server health...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy and running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def login_to_system():
    """Login to the system and return session"""
    print("🔐 Logging in to system...")
    
    session = requests.Session()
    
    # Try login with default credentials
    login_data = {
        "username": "Dr. Rajesh Kumar",
        "password": "rajesh@123",
        "email": "rajesh@example.com"
    }
    
    try:
        response = session.post("http://localhost:8000/auth/login", json=login_data, timeout=10)
        
        if response.status_code == 200:
            print("✅ Successfully logged in")
            return session
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Login error: {e}")
        return None

def create_test_image_with_medical_text():
    """Create a simple test image with medical text"""
    print("🖼️ Creating test image with medical text...")
    
    try:
        # Create a white image
        img = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a better font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            title_font = ImageFont.truetype("arial.ttf", 32)
        except:
            try:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()
            except:
                print("⚠️ Using basic font rendering")
                font = None
                title_font = None
        
        # Add medical text content
        title = "SAPHRIS (asenapine) DOSAGE INFORMATION"
        content = [
            "",
            "RECOMMENDED DOSAGE:",
            "• Schizophrenia: 5 mg twice daily",
            "• Bipolar I Disorder: 10 mg twice daily", 
            "• Maximum dose: 10 mg twice daily",
            "",
            "ADMINISTRATION:",
            "• Sublingual tablets only",
            "• Do not eat or drink for 10 minutes after",
            "• Store at room temperature",
            "",
            "CONTRAINDICATIONS:",
            "• Severe hepatic impairment",
            "• Known hypersensitivity to asenapine"
        ]
        
        # Draw title
        if title_font:
            draw.text((50, 30), title, fill='black', font=title_font)
        else:
            draw.text((50, 30), title, fill='black')
        
        # Draw content
        y_position = 80
        for line in content:
            if font:
                draw.text((50, y_position), line, fill='black', font=font)
            else:
                draw.text((50, y_position), line, fill='black')
            y_position += 25
            
        # Save the test image
        test_image_path = "test_saphris_dosage.png"
        img.save(test_image_path)
        print(f"✅ Created test image: {test_image_path}")
        return test_image_path
        
    except Exception as e:
        print(f"❌ Error creating test image: {e}")
        return None

def upload_image_with_session(session, image_path):
    """Upload an image file to the server using authenticated session"""
    print(f"📤 Uploading image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return False
        
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f, 'image/png')}
            response = session.post("http://localhost:8000/upload", files=files, timeout=60)
            
        if response.status_code == 200:
            print("✅ Image uploaded successfully")
            result = response.json()
            print(f"   Message: {result.get('message', 'No message')}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload error: {e}")
        return False

def test_image_query_with_session(session, query, expected_keywords=None):
    """Test a query using authenticated session and check if it retrieves from the uploaded image"""
    print(f"🔍 Testing query: '{query}'")
    
    try:
        # Send the query using the authenticated session
        query_data = {"question": query}
        response = session.post("http://localhost:8000/ask", json=query_data, timeout=45)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            sources = result.get('sources', [])
            
            print("✅ Query executed successfully")
            print(f"   Answer length: {len(answer)} characters")
            print(f"   Number of sources: {len(sources)}")
            
            # Check sources for image vs PDF citations
            image_sources = []
            pdf_sources = []
            other_sources = []
            
            for s in sources:
                source_name = s.get('source', '').lower()
                if source_name.endswith('.png') or source_name.endswith('.jpg') or source_name.endswith('.jpeg'):
                    image_sources.append(s)
                elif source_name.endswith('.pdf'):
                    pdf_sources.append(s)
                else:
                    other_sources.append(s)
            
            print(f"   📸 Image sources: {len(image_sources)}")
            print(f"   📄 PDF sources: {len(pdf_sources)}")
            print(f"   📎 Other sources: {len(other_sources)}")
            
            # Print detailed source information
            for i, source in enumerate(sources):
                source_name = source.get('source', 'Unknown')
                score = source.get('score', 0)
                content_preview = source.get('content', '')[:100] + "..." if len(source.get('content', '')) > 100 else source.get('content', '')
                print(f"   Source {i+1}: {source_name} (score: {score:.3f})")
                print(f"     Content: {content_preview}")
            
            # Check if expected keywords are in the answer
            if expected_keywords:
                found_keywords = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
                missed_keywords = [kw for kw in expected_keywords if kw.lower() not in answer.lower()]
                print(f"   ✅ Keywords found: {found_keywords}")
                if missed_keywords:
                    print(f"   ❌ Keywords missed: {missed_keywords}")
                
            # Analyze the result
            if image_sources and not pdf_sources:
                print("🎉 PERFECT: Only image sources cited!")
                return "perfect"
            elif image_sources and pdf_sources:
                print("⚠️ MIXED: Both image and PDF sources cited")
                return "mixed"
            elif pdf_sources and not image_sources:
                print("❌ PROBLEM: Only PDF sources cited (should be image)")
                return "pdf_only"
            else:
                print("❌ NO_SOURCES: No sources found")
                return "no_sources"
                
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return "error"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Query error: {e}")
        return "error"

def run_comprehensive_test():
    """Run a comprehensive test of image ingestion and retrieval"""
    print("🧪 Running comprehensive image ingestion test")
    print("=" * 60)
    
    # Step 1: Check server health
    if not test_server_health():
        print("❌ Server not available. Please start the server first.")
        return False
    
    print()
    
    # Step 2: Login to system
    session = login_to_system()
    if not session:
        print("❌ Could not login to system")
        return False
    
    print()
    
    # Step 3: Create and upload test image
    test_image = create_test_image_with_medical_text()
    if not test_image:
        print("❌ Could not create test image")
        return False
    
    print()
    
    # Step 4: Upload the image with authentication
    if not upload_image_with_session(session, test_image):
        print("❌ Could not upload test image")
        return False
    
    print()
    print("⏱️ Waiting 8 seconds for indexing to complete...")
    time.sleep(8)
    print()
    
    # Step 5: Test various queries
    test_queries = [
        {
            "query": "SAPHRIS dosage for schizophrenia",
            "keywords": ["5 mg", "twice daily", "schizophrenia"]
        },
        {
            "query": "asenapine bipolar dosage",
            "keywords": ["10 mg", "bipolar", "twice daily"]
        },
        {
            "query": "SAPHRIS administration instructions",
            "keywords": ["sublingual", "10 minutes", "eat or drink"]
        },
        {
            "query": "asenapine contraindications",
            "keywords": ["hepatic impairment", "hypersensitivity"]
        }
    ]
    
    results = []
    for i, test in enumerate(test_queries):
        print(f"Test {i+1}/4:")
        result = test_image_query_with_session(session, test["query"], test["keywords"])
        results.append(result)
        print()
        time.sleep(3)  # Brief pause between queries
    
    # Step 6: Analyze overall results
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 40)
    
    perfect_count = results.count("perfect")
    mixed_count = results.count("mixed") 
    pdf_only_count = results.count("pdf_only")
    no_sources_count = results.count("no_sources")
    error_count = results.count("error")
    
    print(f"🎉 Perfect (image only): {perfect_count}/{len(results)}")
    print(f"⚠️ Mixed (image + PDF): {mixed_count}/{len(results)}")
    print(f"❌ PDF only (problem): {pdf_only_count}/{len(results)}")
    print(f"❓ No sources: {no_sources_count}/{len(results)}")
    print(f"💥 Errors: {error_count}/{len(results)}")
    
    # Overall assessment
    if perfect_count == len(results):
        print("\n🏆 EXCELLENT: All queries returned only image sources!")
        print("   ✅ Image ingestion is working perfectly!")
    elif perfect_count + mixed_count == len(results):
        print("\n👍 GOOD: All queries found image sources (some mixed with PDFs)")
        print("   ⚠️ Consider adjusting scoring to prioritize images")
    elif pdf_only_count > 0:
        print("\n⚠️ ISSUE: Some queries only returned PDF sources instead of images")
        print("   🔧 Image indexing or retrieval may need adjustment")
    else:
        print("\n❌ MAJOR ISSUE: Image ingestion may not be working properly")
        print("   🚨 Check OCR processing and indexing")
    
    # Cleanup
    if os.path.exists(test_image):
        os.remove(test_image)
        print(f"\n🧹 Cleaned up test image: {test_image}")
    
    return True

def quick_image_test(image_path):
    """Quick test with a specific image file using authentication"""
    print(f"⚡ Quick test with: {image_path}")
    print("=" * 40)
    
    if not test_server_health():
        return False
    
    session = login_to_system()
    if not session:
        print("❌ Could not login to system")
        return False
    
    if not upload_image_with_session(session, image_path):
        return False
    
    print("⏱️ Waiting 5 seconds for indexing...")
    time.sleep(5)
    
    query = input("Enter a query about the image content: ").strip()
    if query:
        test_image_query_with_session(session, query)
    
    return True

def main():
    """Main testing function"""
    print("🧪 Medical RAG Chatbot - Image Ingestion Tester (Fixed)")
    print("=" * 60)
    
    print("Choose test option:")
    print("1. Comprehensive test (creates test image and runs multiple queries)")
    print("2. Quick test with existing image file")
    print("3. Server health check only")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            run_comprehensive_test()
            
        elif choice == "2":
            image_path = input("Enter path to image file: ").strip()
            # Remove quotes if user added them
            image_path = image_path.strip('"').strip("'")
            if image_path:
                quick_image_test(image_path)
            else:
                print("❌ No image path provided")
                
        elif choice == "3":
            test_server_health()
            
        elif choice == "4":
            print("👋 Exiting tester")
            return
            
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n👋 Test cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
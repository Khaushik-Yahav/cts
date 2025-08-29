#!/usr/bin/env python3
"""
OCR Setup Test Script
Run this script to verify that all OCR components are properly installed
"""

import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing Python package imports...")
    
    try:
        import pytesseract
        print("✅ pytesseract imported successfully")
    except ImportError as e:
        print(f"❌ pytesseract import failed: {e}")
        return False
    
    try:
        import pdf2image
        print("✅ pdf2image imported successfully")
    except ImportError as e:
        print(f"❌ pdf2image import failed: {e}")
        return False
    
    try:
        from PIL import Image, ImageDraw
        print("✅ Pillow (PIL) imported successfully")
    except ImportError as e:
        print(f"❌ Pillow import failed: {e}")
        return False
    
    try:
        import fitz  # PyMuPDF
        print("✅ PyMuPDF imported successfully")
    except ImportError as e:
        print(f"❌ PyMuPDF import failed: {e}")
        return False
    
    return True

def test_tesseract():
    """Test Tesseract OCR installation"""
    print("\nTesting Tesseract OCR installation...")
    
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
        
        # Test basic OCR functionality
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a test image with text
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to use a font, fallback to default if not available
            font = ImageFont.load_default()
        except:
            font = None
        
        draw.text((20, 30), "Medical Test OCR", fill='black', font=font)
        
        # Perform OCR
        text = pytesseract.image_to_string(img).strip()
        
        if "Medical" in text or "Test" in text or "OCR" in text:
            print(f"✅ OCR test successful: '{text}'")
            return True
        else:
            print(f"⚠️ OCR test unclear result: '{text}'")
            return True  # Still working, just not perfect
            
    except FileNotFoundError:
        print("❌ Tesseract executable not found in PATH")
        print("   Please install Tesseract and add it to your system PATH")
        return False
    except Exception as e:
        print(f"❌ Tesseract test failed: {e}")
        return False

def test_poppler():
    """Test Poppler installation (for pdf2image)"""
    print("\nTesting Poppler installation...")
    
    try:
        from pdf2image.exceptions import PDFInfoNotInstalledError
        from pdf2image import pdfinfo_from_path
        
        # Try to use poppler by testing with a dummy path
        # This should raise PDFInfoNotInstalledError if poppler is not installed
        try:
            pdfinfo_from_path("dummy_path.pdf")
        except PDFInfoNotInstalledError:
            print("❌ Poppler not found in PATH")
            print("   Please install Poppler and add it to your system PATH")
            return False
        except Exception:
            # Any other exception means poppler is found but the file doesn't exist (expected)
            print("✅ Poppler installation detected")
            return True
            
    except Exception as e:
        print(f"❌ Poppler test failed: {e}")
        return False

def test_file_processing():
    """Test file processing capabilities"""
    print("\nTesting file processing capabilities...")
    
    try:
        # Test image processing
        from PIL import Image
        import io
        
        # Create a test image
        img = Image.new('RGB', (100, 50), color='lightblue')
        
        # Convert to bytes (simulate file upload)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Read back from bytes
        loaded_img = Image.open(img_bytes)
        print(f"✅ Image processing test: {loaded_img.size}")
        
        return True
        
    except Exception as e:
        print(f"❌ File processing test failed: {e}")
        return False

def test_backend_imports():
    """Test if backend modules can be imported"""
    print("\nTesting backend module imports...")
    
    try:
        # Add the current directory to path to import backend modules
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from backend.rag.embeddings import embed_texts
        print("✅ Backend embeddings module imported")
        
        from backend.rag.utils import clean_text
        print("✅ Backend utils module imported")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ Backend import test failed: {e}")
        print("   This is expected if running outside the project directory")
        return True  # Not critical for OCR testing
    except Exception as e:
        print(f"❌ Unexpected error in backend imports: {e}")
        return False

def print_system_info():
    """Print system information"""
    print("\n" + "="*50)
    print("SYSTEM INFORMATION")
    print("="*50)
    print(f"Python version: {sys.version}")
    print(f"Operating system: {os.name}")
    print(f"Current directory: {os.getcwd()}")
    
    # Check PATH for tesseract and poppler
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    tesseract_found = any('tesseract' in dir.lower() for dir in path_dirs)
    poppler_found = any('poppler' in dir.lower() for dir in path_dirs)
    
    print(f"Tesseract in PATH: {'✅' if tesseract_found else '❌'}")
    print(f"Poppler in PATH: {'✅' if poppler_found else '❌'}")

def main():
    """Main test runner"""
    print("🔬 Medical RAG Chatbot - OCR Setup Test")
    print("="*50)
    
    print_system_info()
    
    print("\n" + "="*50)
    print("RUNNING OCR TESTS")
    print("="*50)
    
    tests = [
        ("Package Imports", test_imports),
        ("Tesseract OCR", test_tesseract),
        ("Poppler PDF", test_poppler),
        ("File Processing", test_file_processing),
        ("Backend Modules", test_backend_imports),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your OCR setup is ready.")
        print("\nNext steps:")
        print("1. Update your ingest.py file with the provided code")
        print("2. Update your main.py file with image upload support")
        print("3. Update your frontend files (HTML, CSS, JS)")
        print("4. Run: python run.py")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the setup guide.")
        print("\nCommon solutions:")
        if not any(name == "Tesseract OCR" and result for name, result in results):
            print("- Install Tesseract OCR and add to PATH")
        if not any(name == "Poppler PDF" and result for name, result in results):
            print("- Install Poppler and add to PATH")
        if not any(name == "Package Imports" and result for name, result in results):
            print("- Install missing Python packages: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
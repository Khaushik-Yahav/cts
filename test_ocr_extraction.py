#!/usr/bin/env python3
"""
OCR Text Extraction Tester
Tests OCR text extraction from image files and gets user verification
"""

import os
import sys
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import cv2
import numpy as np

def preprocess_image_basic(image_path):
    """Basic image preprocessing for better OCR"""
    try:
        # Open image with PIL
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img
    except Exception as e:
        print(f"❌ Error opening image: {e}")
        return None

def preprocess_image_enhanced(image_path):
    """Enhanced image preprocessing for better OCR"""
    try:
        # Read image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Could not read image: {image_path}")
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply threshold to get black and white image
        _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL Image
        pil_img = Image.fromarray(threshold)
        
        return pil_img
    except Exception as e:
        print(f"❌ Error in enhanced preprocessing: {e}")
        # Fall back to basic preprocessing
        return preprocess_image_basic(image_path)

def extract_text_basic(image):
    """Extract text using basic OCR"""
    try:
        text = pytesseract.image_to_string(image, lang='eng')
        return text.strip()
    except Exception as e:
        print(f"❌ Error in basic OCR: {e}")
        return None

def extract_text_with_config(image):
    """Extract text using OCR with custom configuration"""
    try:
        # Custom config for better medical text recognition
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,():;-•/% '
        text = pytesseract.image_to_string(image, config=custom_config, lang='eng')
        return text.strip()
    except Exception as e:
        print(f"❌ Error in configured OCR: {e}")
        return None

def extract_text_multiple_methods(image_path):
    """Try multiple OCR methods and return all results"""
    results = {}
    
    print("🔍 Trying multiple OCR methods...")
    
    # Method 1: Basic preprocessing + Basic OCR
    print("   Method 1: Basic preprocessing + Basic OCR")
    img_basic = preprocess_image_basic(image_path)
    if img_basic:
        text_basic = extract_text_basic(img_basic)
        results['basic'] = text_basic
        print(f"   ✅ Basic method completed: {len(text_basic) if text_basic else 0} characters")
    
    # Method 2: Enhanced preprocessing + Basic OCR
    print("   Method 2: Enhanced preprocessing + Basic OCR")
    img_enhanced = preprocess_image_enhanced(image_path)
    if img_enhanced:
        text_enhanced = extract_text_basic(img_enhanced)
        results['enhanced'] = text_enhanced
        print(f"   ✅ Enhanced method completed: {len(text_enhanced) if text_enhanced else 0} characters")
    
    # Method 3: Basic preprocessing + Configured OCR
    print("   Method 3: Basic preprocessing + Configured OCR")
    if img_basic:
        text_configured = extract_text_with_config(img_basic)
        results['configured'] = text_configured
        print(f"   ✅ Configured method completed: {len(text_configured) if text_configured else 0} characters")
    
    # Method 4: Enhanced preprocessing + Configured OCR
    print("   Method 4: Enhanced preprocessing + Configured OCR")
    if img_enhanced:
        text_both = extract_text_with_config(img_enhanced)
        results['both_enhanced'] = text_both
        print(f"   ✅ Both enhanced method completed: {len(text_both) if text_both else 0} characters")
    
    return results

def display_results(results):
    """Display all OCR results for comparison"""
    print("\n" + "="*80)
    print("📋 OCR RESULTS COMPARISON")
    print("="*80)
    
    method_names = {
        'basic': 'Method 1: Basic preprocessing + Basic OCR',
        'enhanced': 'Method 2: Enhanced preprocessing + Basic OCR', 
        'configured': 'Method 3: Basic preprocessing + Configured OCR',
        'both_enhanced': 'Method 4: Enhanced preprocessing + Configured OCR'
    }
    
    for method, text in results.items():
        print(f"\n🔬 {method_names.get(method, method)}:")
        print("-" * 60)
        
        if text and text.strip():
            # Show first 200 characters as preview
            preview = text[:200] + "..." if len(text) > 200 else text
            print(f"Length: {len(text)} characters")
            print(f"Preview: {preview}")
            print(f"Full text:\n{text}")
        else:
            print("❌ No text extracted or empty result")
        
        print("-" * 60)

def get_user_feedback():
    """Get user feedback on OCR results"""
    print("\n" + "="*80)
    print("🤔 USER FEEDBACK")
    print("="*80)
    
    print("Please review the OCR results above and answer the following:")
    print()
    
    # Ask which method worked best
    print("1. Which method extracted text most accurately?")
    print("   a) Method 1 (Basic + Basic)")
    print("   b) Method 2 (Enhanced + Basic)")
    print("   c) Method 3 (Basic + Configured)")
    print("   d) Method 4 (Enhanced + Configured)")
    print("   e) None worked well")
    
    best_method = input("\nEnter your choice (a/b/c/d/e): ").strip().lower()
    
    # Ask about accuracy
    print("\n2. How accurate was the best method?")
    print("   a) Perfect (100% accurate)")
    print("   b) Very good (90-99% accurate)")
    print("   c) Good (70-89% accurate)")
    print("   d) Poor (50-69% accurate)")
    print("   e) Very poor (<50% accurate)")
    
    accuracy = input("\nEnter your choice (a/b/c/d/e): ").strip().lower()
    
    # Ask about specific issues
    print("\n3. What specific issues did you notice? (select all that apply)")
    print("   Type the letters for issues you saw:")
    print("   a) Missing characters")
    print("   b) Wrong characters")
    print("   c) Extra spaces")
    print("   d) Missing spaces")
    print("   e) Numbers misread as letters")
    print("   f) Letters misread as numbers")
    print("   g) Punctuation issues")
    print("   h) Line breaks in wrong places")
    print("   i) No major issues")
    
    issues = input("\nEnter issue letters (e.g., 'abc'): ").strip().lower()
    
    return {
        'best_method': best_method,
        'accuracy': accuracy,
        'issues': list(issues)
    }

def provide_recommendations(feedback):
    """Provide recommendations based on user feedback"""
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    method_mapping = {
        'a': 'basic',
        'b': 'enhanced', 
        'c': 'configured',
        'd': 'both_enhanced'
    }
    
    best_method = method_mapping.get(feedback['best_method'], 'unknown')
    accuracy = feedback['accuracy']
    issues = feedback['issues']
    
    print(f"Based on your feedback:")
    print(f"✅ Best method: {best_method}")
    print(f"📊 Accuracy level: {accuracy}")
    print(f"⚠️ Issues found: {issues}")
    print()
    
    # Provide specific recommendations
    if accuracy in ['a', 'b']:  # Perfect or very good
        print("🎉 Great! OCR is working well for your image type.")
        print("📝 Recommendations for your pipeline:")
        print(f"   - Use the {best_method} preprocessing method")
        print("   - Current OCR setup should work fine")
        print("   - You can proceed with confidence")
        
    elif accuracy == 'c':  # Good
        print("👍 OCR is working reasonably well.")
        print("📝 Recommendations for your pipeline:")
        print(f"   - Use the {best_method} preprocessing method")
        print("   - Consider image quality improvements")
        print("   - May need some post-processing cleanup")
        
    elif accuracy in ['d', 'e']:  # Poor or very poor
        print("⚠️ OCR accuracy needs improvement.")
        print("📝 Recommendations for your pipeline:")
        print("   - Try higher resolution images (300+ DPI)")
        print("   - Ensure good contrast (black text on white background)")
        print("   - Consider manual image cleanup before OCR")
        print("   - May need different OCR engine or settings")
    
    # Specific issue recommendations
    if 'a' in issues or 'b' in issues:  # Missing/wrong characters
        print("   - Try different OCR page segmentation modes")
        print("   - Consider character confidence thresholds")
    
    if 'c' in issues or 'd' in issues:  # Space issues
        print("   - May need custom text post-processing")
        print("   - Consider word-level OCR analysis")
    
    if 'e' in issues or 'f' in issues:  # Number/letter confusion
        print("   - Use character whitelisting for specific content")
        print("   - Consider domain-specific OCR training")
    
    print("\n🔧 Next steps:")
    print("1. Test with more images of the same type")
    print("2. Integrate the best method into your pipeline")
    print("3. Add error handling for failed extractions")
    print("4. Consider batch processing optimizations")

def main():
    """Main function"""
    print("🔍 OCR Text Extraction Tester")
    print("="*50)
    print("This tool will test OCR text extraction from your image file")
    print("and help optimize the extraction method for your use case.")
    print()
    
    # Get image file path
    while True:
        image_path = input("📁 Enter path to image file (.png, .jpg, .jpeg): ").strip()
        
        # Remove quotes if user added them
        image_path = image_path.strip('"').strip("'")
        
        if not image_path:
            print("❌ Please enter a file path")
            continue
            
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            continue
            
        # Check file extension
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg']:
            print(f"❌ Unsupported file type: {ext}")
            print("   Please use .png, .jpg, or .jpeg files")
            continue
            
        break
    
    print(f"\n✅ Processing image: {os.path.basename(image_path)}")
    print(f"   Full path: {image_path}")
    
    # Extract text using multiple methods
    results = extract_text_multiple_methods(image_path)
    
    if not any(results.values()):
        print("\n❌ No text could be extracted using any method")
        print("💡 Suggestions:")
        print("   - Check if image contains readable text")
        print("   - Try a higher resolution image")
        print("   - Ensure good contrast between text and background")
        return
    
    # Display results
    display_results(results)
    
    # Get user feedback
    feedback = get_user_feedback()
    
    # Provide recommendations
    provide_recommendations(feedback)
    
    print(f"\n✅ Testing completed for: {os.path.basename(image_path)}")
    print("🚀 You can now integrate the recommended method into your pipeline!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Testing cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("💡 Please check your image file and try again")
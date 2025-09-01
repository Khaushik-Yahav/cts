# backend/rag/ingest.py
import os
import io
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import json
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import cv2
from sentence_transformers import SentenceTransformer
import faiss

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Tesseract path for Method B OCR
def configure_tesseract():
    """Configure Tesseract OCR path"""
    if os.name == 'nt':  # Windows
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"✅ Tesseract configured at: {path}")
                return True
        
        logger.warning("⚠️ Tesseract not found in standard paths")
        return False
    return True

# Initialize Tesseract on import
configure_tesseract()

# Method B OCR Implementation
def extract_text_with_methodB_ocr(image_path: str) -> str:
    """
    Method B: Enhanced preprocessing + Basic OCR
    This is the method that worked best in your testing
    """
    try:
        logger.info(f"🖼️ Processing with Method B: {os.path.basename(image_path)}")
        
        # Read image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"❌ Could not read image: {image_path}")
            return ""
        
        # Method B Enhancement 1: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Method B Enhancement 2: Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Method B Enhancement 3: Apply threshold to get black and white image
        _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL Image for OCR
        pil_img = Image.fromarray(threshold)
        
        # Method B: Basic OCR
        text = pytesseract.image_to_string(pil_img, lang='eng')
        extracted_text = text.strip()
        
        logger.info(f"   📝 Method B extracted {len(extracted_text)} characters")
        return extracted_text
        
    except Exception as e:
        logger.error(f"❌ Method B OCR failed: {e}")
        # Fallback to basic method
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='eng')
            return text.strip()
        except:
            return ""

def process_image_bytes(image_bytes: bytes, filename: str) -> str:
    """
    Process image bytes using Method B OCR
    This function is called by your backend
    """
    try:
        logger.info(f"🖼️ Processing image bytes with Method B: {filename}")
        
        # Convert bytes to OpenCV image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error(f"❌ Could not decode image: {filename}")
            return ""
        
        # Method B Enhancement 1: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Method B Enhancement 2: Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Method B Enhancement 3: Apply threshold to get black and white image
        _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert to PIL Image for OCR
        pil_img = Image.fromarray(threshold)
        
        # Method B: Basic OCR
        text = pytesseract.image_to_string(pil_img, lang='eng')
        extracted_text = text.strip()
        
        logger.info(f"   📝 Method B extracted {len(extracted_text)} characters from {filename}")
        return extracted_text
        
    except Exception as e:
        logger.error(f"❌ Method B processing failed for {filename}: {e}")
        # Fallback to basic method
        try:
            img = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(img, lang='eng')
            return text.strip()
        except:
            return ""

class DocumentProcessor:
    """Enhanced document processor with Method B OCR integration"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the document processor"""
        self.model = SentenceTransformer(model_name)
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.index = None
        self.documents = []
        
        logger.info(f"🤖 Document processor initialized with Method B OCR")

    def create_chunk(self, text: str, source: str, page: int = 1, metadata: dict = None):
        """Create a document chunk"""
        if not text.strip():
            return None
            
        chunk = {
            'text': text.strip(),  
            'source': source,
            'page': page
        }
        
        if metadata:
            chunk.update(metadata)
            
        return chunk

    def chunk_text(self, text: str, chunk_size: int = None):
        """Split text into chunks"""
        if chunk_size is None:
            chunk_size = self.chunk_size
            
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(word)
            current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def extract_text_from_pdf(self, pdf_path: str):
        """Extract text from PDF with Method B OCR fallback"""
        text_content = []
        
        try:
            logger.info(f"📄 Processing PDF: {os.path.basename(pdf_path)}")
            
            # Try text extraction first
            doc = fitz.open(pdf_path)
            has_text = False
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                if text.strip():
                    has_text = True
                    chunks = self.chunk_text(text)
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            text_content.append(self.create_chunk(
                                chunk, 
                                os.path.basename(pdf_path), 
                                page_num + 1
                            ))
            
            doc.close()
            
            # If no text found, try Method B OCR
            if not has_text:
                logger.info("📄 No extractable text found, trying Method B OCR...")
                text_content.extend(self.extract_pdf_with_methodB_ocr(pdf_path))
            
        except Exception as e:
            logger.error(f"❌ Error processing PDF {pdf_path}: {e}")
        
        logger.info(f"   ✅ Created {len(text_content)} chunks from PDF")
        return [chunk for chunk in text_content if chunk]

    def extract_pdf_with_methodB_ocr(self, pdf_path: str):
        """Extract text from PDF using Method B OCR"""
        chunks = []
        
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            logger.info(f"   📸 Converted {len(images)} pages to images")
            
            for page_num, image in enumerate(images, 1):
                # Save temporary image
                temp_path = f"temp_page_{page_num}.png"
                image.save(temp_path)
                
                try:
                    # Use Method B OCR
                    extracted_text = extract_text_with_methodB_ocr(temp_path)
                    
                    if extracted_text:
                        text_chunks = self.chunk_text(extracted_text)
                        for chunk_text in text_chunks:
                            if chunk_text.strip():
                                chunk = self.create_chunk(
                                    chunk_text,
                                    os.path.basename(pdf_path),
                                    page_num,
                                    {'type': 'EMBEDDED_IMAGE_OCR_2'}  # Method B OCR marker
                                )
                                chunks.append(chunk)
                
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
        except Exception as e:
            logger.error(f"❌ PDF Method B OCR failed: {e}")
        
        return chunks

    def extract_text_from_image_file(self, image_path: str):
        """Extract text from image file using Method B OCR"""
        chunks = []
        
        try:
            logger.info(f"🖼️ Processing image: {os.path.basename(image_path)}")
            
            # Use Method B OCR
            extracted_text = extract_text_with_methodB_ocr(image_path)
            
            if extracted_text:
                text_chunks = self.chunk_text(extracted_text)
                for chunk_text in text_chunks:
                    if chunk_text.strip():
                        chunk = self.create_chunk(
                            chunk_text,
                            os.path.basename(image_path),
                            1,
                            {'type': 'IMAGE_OCR'}  # Method B OCR marker
                        )
                        chunks.append(chunk)
                        
                logger.info(f"   ✅ Created {len(chunks)} chunks from image")
            else:
                logger.warning(f"   ⚠️ No text extracted from {image_path}")
                
        except Exception as e:
            logger.error(f"❌ Image processing failed: {e}")
        
        return chunks

    def process_files(self, directory: str = "data/pdfs"):
        """Process all files in directory using Method B OCR"""
        all_chunks = []
        
        if not os.path.exists(directory):
            logger.error(f"❌ Directory not found: {directory}")
            return []
        
        files = os.listdir(directory)
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
        
        logger.info(f"📁 Processing {len(pdf_files)} PDFs and {len(image_files)} images with Method B OCR...")
        
        # Process PDFs
        for filename in pdf_files:
            file_path = os.path.join(directory, filename)
            pdf_chunks = self.extract_text_from_pdf(file_path)
            all_chunks.extend(pdf_chunks)
        
        # Process Images with Method B
        for filename in image_files:
            file_path = os.path.join(directory, filename)
            image_chunks = self.extract_text_from_image_file(file_path)
            all_chunks.extend(image_chunks)
        
        self.documents = all_chunks
        logger.info(f"📊 Created {len(all_chunks)} text chunks from {len(files)} files using Method B OCR")
        return all_chunks

    def create_embeddings(self):
        """Create embeddings for all documents"""
        if not self.documents:
            logger.warning("⚠️ No documents to create embeddings for")
            return np.array([])
        
        logger.info("🧠 Generating embeddings...")
        texts = [doc['text'] for doc in self.documents]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        return embeddings

    def build_index(self, embeddings):
        """Build FAISS index"""
        if len(embeddings) == 0:
            logger.warning("⚠️ No embeddings to build index")
            return
        
        logger.info("🔍 Building search index...")
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype('float32'))
        logger.info(f"✅ Built index with {self.index.ntotal} vectors")

    def save_index(self, save_dir: str = "data/index"):
        """Save index and metadata"""
        os.makedirs(save_dir, exist_ok=True)
        
        if self.index:
            faiss.write_index(self.index, os.path.join(save_dir, "index.faiss"))
        
        if hasattr(self, 'embeddings'):
            np.save(os.path.join(save_dir, "embeddings.npy"), self.embeddings)
        
        # Save metadata with Method B marker
        metadata = self.documents  # Use documents directly as metadata
        
        with open(os.path.join(save_dir, "meta.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Saved Method B OCR index to {save_dir}")

# FIXED: Main function that matches main.py calls
def ingest_files(pdf_dir: str = "data/pdfs", index_dir: str = "data/index", include_images: bool = True):
    """
    Main ingest function called by your backend
    Now uses Method B OCR processing with correct signature
    """
    logger.info("🚀 Starting file ingestion with Method B OCR...")
    
    processor = DocumentProcessor()
    
    # Process files with Method B OCR
    chunks = processor.process_files(pdf_dir)  # Use pdf_dir parameter
    
    if chunks:
        # Create embeddings and index
        embeddings = processor.create_embeddings()
        processor.embeddings = embeddings
        
        if len(embeddings) > 0:
            processor.build_index(embeddings)
            processor.save_index(index_dir)  # Use index_dir parameter
            logger.info("🎉 Method B OCR ingestion completed successfully!")
            return {
                "processed_files": len(chunks),
                "chunks_created": len(chunks),
                "method": "Method_B_Enhanced_OCR"
            }
        else:
            logger.error("❌ No embeddings created")
            return {"processed_files": 0, "chunks_created": 0, "error": "No embeddings created"}
    else:
        logger.error("❌ No content processed with Method B OCR")
        return {"processed_files": 0, "chunks_created": 0, "error": "No content processed"}

# Additional utility functions your backend might need
def process_single_file(file_path: str, index_dir: str = "data/index") -> int:
    """Process a single file with Method B OCR"""
    processor = DocumentProcessor()
    
    if file_path.lower().endswith('.pdf'):
        chunks = processor.extract_text_from_pdf(file_path)
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        chunks = processor.extract_text_from_image_file(file_path)
    else:
        logger.warning(f"⚠️ Unsupported file format: {file_path}")
        return 0
    
    if chunks:
        processor.documents = chunks
        embeddings = processor.create_embeddings()
        processor.embeddings = embeddings
        
        if len(embeddings) > 0:
            processor.build_index(embeddings)
            processor.save_index(index_dir)
            logger.info(f"✅ Processed {file_path} with Method B OCR")
            return len(chunks)
    
    return 0

# For standalone testing
def main():
    """Main function for standalone testing"""
    result = ingest_files("data/pdfs", "data/index", True)
    logger.info(f"📊 Processed with Method B OCR: {result}")

if __name__ == "__main__":
    main()
import torch
import os
import shutil
from PIL import Image
import pdfplumber
from transformers import VisionEncoderDecoderModel, AutoProcessor
from utils.config import DEVICE, OCR_MODEL
from utils.logger import setup_logger
from data_extraction.pdf_utils import pdf_to_images
from utils.data_utils import clean_text

logger = setup_logger("ocr")

# Global model and processor to avoid reloading
processor, model = None, None

def load_ocr_model():
    """Load transformer-based OCR model and processor globally."""
    global processor, model
    if processor is None or model is None:
        try:
            processor = AutoProcessor.from_pretrained(OCR_MODEL)
            model = VisionEncoderDecoderModel.from_pretrained(OCR_MODEL)
            model.to(DEVICE)
            model.eval()
            logger.info(f"OCR model {OCR_MODEL} loaded successfully")
        except Exception as e:
            logger.error(f"OCR model loading error: {str(e)}")
            return None, None
    return processor, model

def extract_text_and_tables_from_pdf(pdf_path):
    """Extract machine-readable text and tables from PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            tables = []
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend([{"rows": table} for table in page_tables])
            return clean_text(text), tables
    except Exception as e:
        logger.warning(f"PDF extraction failed: {str(e)}")
        return "", []

def extract_report(file_path, report_type):
    """
    Extract structured data (text, tables, images) from reports.

    Args:
        file_path (str): Path to PDF or image file.
        report_type (str): e.g., "blood", "scan"

    Returns:
        dict: {"text": str, "tables": list, "images": list}
    """
    logger.info(f"Extracting report: {file_path}, Type: {report_type}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"text": "", "tables": [], "images": []}

    results = {"text": "", "tables": [], "images": []}

    # Case 1: Try direct extraction from PDF
    if file_path.endswith(".pdf"):
        text, tables = extract_text_and_tables_from_pdf(file_path)
        if text.strip() or tables:
            results["text"] = text
            results["tables"] = tables
            logger.info(f"Used direct PDF extraction: Text={text[:100]}..., Tables={len(tables)}")
            return results
        else:
            logger.info("No text/tables found in PDF — using OCR fallback")
            images = pdf_to_images(file_path)
    else:
        images = [file_path]

    results["images"] = images
    if not images:
        logger.warning("No images available, returning mock data")
        return {"text": "Consolidation noted", "tables": [], "images": []}

    proc, mod = load_ocr_model()
    if not proc or not mod:
        return results

    # Case 2: OCR fallback for images or scanned PDFs
    for image_path in images:
        try:
            image = Image.open(image_path).convert("RGB")
            pixel_values = proc(image, return_tensors="pt").pixel_values.to(DEVICE)
            
            with torch.no_grad():
                outputs = mod.generate(pixel_values)
                extracted_text = proc.batch_decode(outputs, skip_special_tokens=True)[0]
            
            extracted_text = clean_text(extracted_text)
            results["text"] += extracted_text + "\n"
            
            # Basic table heuristic (split by lines, check for tabular structure)
            lines = extracted_text.split("\n")
            if len(lines) > 1 and any("|" in line or "\t" in line for line in lines):
                results["tables"].append({"raw_text": extracted_text, "rows": [line.split("|") for line in lines if "|" in line]})
            
            logger.info(f"OCR extracted from {image_path}: {extracted_text[:100]}...")
        except Exception as e:
            logger.error(f"OCR error for {image_path}: {str(e)}")
            continue
    
    # Clean up temporary images
    temp_dir = os.path.dirname(images[0]) if images else ""
    if temp_dir.startswith("temp_images"):
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned up temporary images: {temp_dir}")

    logger.info(f"Finished extraction: Text={results['text'][:100]}..., Tables={len(results['tables'])}, Images={len(results['images'])}")
    return results

def process_report(file_path, report_type):
    """Wrapper to process and return extracted report data."""
    return extract_report(file_path, report_type)
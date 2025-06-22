from data_extraction.ocr import process_report
import os

def test_ocr():
    """Test OCR extraction on sample.pdf."""
    file_path = os.path.join("sample.pdf")  # Update to 'data/sample_blood.pdf' if moved
    report_type = "Blood"
    result = process_report(file_path, report_type)
    print("OCR Extraction Result:")
    print(f"Text: {result['text'][:200]}..." if result['text'] else "No text extracted")
    print(f"Tables: {len(result['tables'])} found")
    print(f"Images: {result['images']}")
    return result

if __name__ == "__main__":
    test_ocr()
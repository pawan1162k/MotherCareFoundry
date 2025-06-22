import os
from pdf2image import convert_from_path
from utils.logger import setup_logger

logger = setup_logger("pdf_utils")

def pdf_to_images(pdf_path):
    """
    Convert PDF to images for OCR processing.

    Args:
        pdf_path (str): Path to PDF file.

    Returns:
        list: Paths to generated images.
    """
    logger.info(f"Converting PDF to images: {pdf_path}")
    try:
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            return []

        # Create temporary directory
        temp_dir = "temp_images"
        os.makedirs(temp_dir, exist_ok=True)

        # Convert PDF to images
        images = convert_from_path(pdf_path)
        image_paths = []

        # Save images
        for i, image in enumerate(images):
            image_path = os.path.join(temp_dir, f"page_{i}.jpg")
            image.save(image_path, "JPEG")
            image_paths.append(image_path)
            logger.info(f"Saved image: {image_path}")

        return image_paths
    except Exception as e:
        logger.error(f"PDF conversion error: {str(e)}")
        return []
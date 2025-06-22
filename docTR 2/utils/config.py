import os
from dotenv import load_dotenv

load_dotenv()

# API keys
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# Model paths
MEDCLIP_MODEL = "RyanWangZf/MedCLIP"
SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OCR_MODEL = "microsoft/donut-base"
OPENBIOLLM_MODEL = "aaditya/Llama3-OpenBioLLM-70B"
DOCTOR_COLLECTION_NAME = "doctor_collection"  

# Chroma settings
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

# Device (CPU-only)
DEVICE = "cpu"
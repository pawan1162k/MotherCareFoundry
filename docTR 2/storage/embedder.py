from sentence_transformers import SentenceTransformer
from utils.config import SENTENCE_TRANSFORMER_MODEL, DEVICE
from utils.logger import setup_logger

logger = setup_logger("embedder")

def load_embedder():
    """Load SentenceTransformer model."""
    try:
        model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, device=DEVICE)
        logger.info(f"SentenceTransformer {SENTENCE_TRANSFORMER_MODEL} loaded")
        return model
    except Exception as e:
        logger.error(f"Embedder loading error: {str(e)}")
        return None

def embed_text(text):
    """Generate embeddings for text."""
    model = load_embedder()
    if not model:
        return []
    try:
        embedding = model.encode([text], convert_to_numpy=True)[0].tolist()
        logger.info(f"Embedded text: {text[:100]}...")
        return embedding
    except Exception as e:
        logger.error(f"Embedding error: {str(e)}")
        return []
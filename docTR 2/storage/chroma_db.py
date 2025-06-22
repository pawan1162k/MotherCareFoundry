import chromadb
from utils.config import CHROMA_PERSIST_DIR
from utils.logger import setup_logger
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import time

logger = setup_logger("chroma_db")

# Initialize ChromaDB client & collection
_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
_collection = _client.get_or_create_collection(
    name="health_history",
    embedding_function=_embed_fn
)

def add_to_health_history(user_id: str, report_type: str, text: str):
    """
    Add a health/fitness record to the history DB.
    """
    try:
        # Create unique ID with timestamp
        timestamp = int(time.time())
        doc_id = f"{user_id}_{report_type}_{timestamp}"
        
        metadata = {
            "user_id": user_id,
            "report_type": report_type,
            "timestamp": str(timestamp)
        }
        
        _collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata]
        )
        logger.info(f"Added to health history: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store health history: {e}")
        return False

def get_health_history(user_id: str, n_results: int = 10):
    """
    Retrieve up to n_results past health/fitness records for a given user.
    """
    try:
        results = _collection.query(
            query_texts=[""],
            n_results=n_results,
            where={"user_id": user_id}
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [{"document": d, "metadata": m} for d, m in zip(docs, metas)]
    except Exception as e:
        logger.error(f"Error retrieving health history for {user_id}: {e}")
        return []
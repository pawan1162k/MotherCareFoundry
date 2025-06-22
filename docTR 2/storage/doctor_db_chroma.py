import chromadb
from utils.config import CHROMA_PERSIST_DIR, DOCTOR_COLLECTION_NAME
from utils.logger import setup_logger
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = setup_logger("doctor_db_chroma")

# Initialize ChromaDB client & collection
_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
_collection = _client.get_or_create_collection(
    name=DOCTOR_COLLECTION_NAME,
    embedding_function=_embed_fn
)

def init_doctor_db():
    """Initialize the doctor collection with sample data."""
    try:
        # Check if collection is empty
        if _collection.count() == 0:
            sample_doctors = [
                {
                    "id": "doc1",
                    "name": "Dr. Alice Smith",
                    "specialty": "General Practitioner",
                    "location": "New York",
                    "phone": "555-0101",
                    "email": "alice@example.com",
                    "description": "General practitioner with 10 years of experience in primary care."
                },
                {
                    "id": "doc2",
                    "name": "Dr. Bob Jones",
                    "specialty": "Pediatrics",
                    "location": "New York",
                    "phone": "555-0102",
                    "email": "bob@example.com",
                    "description": "Pediatrician specializing in child healthcare."
                },
                {
                    "id": "doc3",
                    "name": "Dr. Carol Lee",
                    "specialty": "Cardiology",
                    "location": "Los Angeles",
                    "phone": "555-0103",
                    "email": "carol@example.com",
                    "description": "Cardiologist with expertise in heart conditions."
                },
                {
                    "id": "doc4",
                    "name": "Dr. David Kim",
                    "specialty": "Dermatology",
                    "location": "Los Angeles",
                    "phone": "555-0104",
                    "email": "david@example.com",
                    "description": "Dermatologist focused on skin health."
                },
                {
                    "id": "doc5",
                    "name": "Dr. Emma Wilson",
                    "specialty": "Orthopedics",
                    "location": "Chicago",
                    "phone": "555-0105",
                    "email": "emma@example.com",
                    "description": "Orthopedic surgeon specializing in joint replacements."
                }
            ]
            # Prepare data for ChromaDB
            ids = [doc["id"] for doc in sample_doctors]
            documents = [f"{doc['specialty']} in {doc['location']}: {doc['description']}" for doc in sample_doctors]
            metadatas = [
                {
                    "name": doc["name"],
                    "specialty": doc["specialty"],
                    "location": doc["location"],
                    "phone": doc["phone"],
                    "email": doc["email"]
                } for doc in sample_doctors
            ]
            _collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info("Doctor collection initialized with sample data")
        else:
            logger.info("Doctor collection already populated")
    except Exception as e:
        logger.error(f"Failed to initialize doctor DB: {e}")
        raise

def get_doctors_by_specialty_and_location(diagnosis: str, location: str, n_results: int = 3) -> list:
    """Query doctors by diagnosis and location using similarity search."""
    try:
        query_text = f"{diagnosis} doctor in {location}"
        results = _collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={"location": location}  # Filter by exact location
        )
        doctors = [
            {
                "name": meta["name"],
                "specialty": meta["specialty"],
                "location": meta["location"],
                "phone": meta["phone"],
                "email": meta["email"]
            }
            for meta in results.get("metadatas", [[]])[0]
        ]
        logger.info(f"Found {len(doctors)} doctors for query: {query_text}")
        return doctors
    except Exception as e:
        logger.error(f"Error querying doctors: {e}")
        return []

# Initialize on import
init_doctor_db()
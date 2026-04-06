from src.vectorStore import ProposalVectorStore
from src.config import Config
import os

def check_db():
    print(f"Checking DB at {Config.CHROMA_DB_PATH}")
    if not os.path.exists(Config.CHROMA_DB_PATH):
        print("DB path does not exist.")
        return

    try:
        pv = ProposalVectorStore()
        # Chroma vector_store doesn't have a direct 'count' in LangChain wrapper easily accessible sometimes
        # but we can try to get all or search
        results = pv.vector_store.similarity_search("test", k=10)
        print(f"Found {len(results)} results for 'test' query.")
        for i, res in enumerate(results):
            print(f"Result {i}: {res.page_content[:50]}... Metadata: {res.metadata}")
            
        # Try to get underlying collection count if possible
        count = pv.vector_store._collection.count()
        print(f"Total documents in collection: {count}")
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    check_db()

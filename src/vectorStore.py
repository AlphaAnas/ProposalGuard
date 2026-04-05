import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import Config

class ProposalVectorStore:
    def __init__(self, collection_name: str = "past_proposals"):
        """Initializes a LangChain-native ChromaDB client with free local embeddings."""
        
        # 1. Initialize the free local embedding model (all-MiniLM-L6-v2)
        # This will download an ~80MB model to your local machine on the very first run.
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # 2. Ensure directory exists to prevent path errors
        os.makedirs(Config.CHROMA_DB_PATH, exist_ok=True)
        
        # 3. Initialize the LangChain Chroma integration
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=Config.CHROMA_DB_PATH
        )
        print(f"✅ LangChain-native Chroma DB ready. Collection '{collection_name}' initialized.")

    def add_proposals(self, texts: list[str], metadatas: list[dict], ids: list[str]):
        """Adds raw text proposals to the local vector database."""
        self.vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        print(f"✅ Added {len(texts)} proposals to the database.")

    def get_retriever(self, num_results: int = 2):
        """
        Returns a standard LangChain retriever object.
        Pass this directly into your LangGraph nodes!
        """
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": num_results}
        )
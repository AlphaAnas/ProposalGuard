import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db_data")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")

    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY or not AZURE_DEPLOYMENT_NAME:
        raise ValueError("AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, and AZURE_DEPLOYMENT_NAME are missing in the .env file")
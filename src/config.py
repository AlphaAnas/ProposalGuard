import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db_data")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is missing in the .env file")
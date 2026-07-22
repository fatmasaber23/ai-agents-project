import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

if not MISTRAL_API_KEY:
    raise ValueError(
        "MISTRAL_API_KEY was not found. Please check your .env file."
    )


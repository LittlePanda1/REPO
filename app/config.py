import os
from dotenv import load_dotenv

load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# Base URL for PDF export links (set in Railway env, stripped of trailing slash)
_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
APP_BASE_URL = _base_url.rstrip("/") if _base_url else "http://localhost:8000"

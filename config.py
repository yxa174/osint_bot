import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Опциональные API ключи
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")  # Have I Been Pwned
ABSTRACT_PHONE_API_KEY = os.getenv("ABSTRACT_PHONE_API_KEY", "")  # Abstract API Phone Validation
NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "")  # NumVerify

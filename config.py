import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Опциональные API ключи (бесплатные)
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")  # Have I Been Pwned — $3.50/мес
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")  # Hunter.io — 25 запросов/мес бесплатно
ABSTRACT_PHONE_API_KEY = os.getenv("ABSTRACT_PHONE_API_KEY", "")  # Abstract API — 200 запросов/мес бесплатно
NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "")  # NumVerify — 250 запросов/мес бесплатно

import os
from dotenv import load_dotenv

load_dotenv()

# Обязательно
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ===== API ключи =====

# Have I Been Pwned — $3.50/мес
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")

# Hunter.io — 25 запросов/мес бесплатно
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# Abstract API Phone — 200 запросов/мес бесплатно
ABSTRACT_PHONE_API_KEY = os.getenv("ABSTRACT_PHONE_API_KEY", "")

# NumVerify — 250 запросов/мес бесплатно
NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "")

# Shodan — 100 результатов/мес бесплатно
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")

# Etherscan — бесплатный ключ (до 5 запросов/сек)
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

# BuiltWith — бесплатный план
BUILTWITH_API_KEY = os.getenv("BUILTWITH_API_KEY", "")

# TimezoneDB — бесплатный план
TIMEZONEDB_API_KEY = os.getenv("TIMEZONEDB_API_KEY", "")

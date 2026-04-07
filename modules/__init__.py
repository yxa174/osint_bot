"""OSINT модули."""

from modules.phone import search_phone_everywhere, validate_phone
from modules.username import search_username, format_username_report, validate_username
from modules.email import search_email_everywhere, validate_email
from modules.name import search_name_everywhere, validate_name
from modules.car import search_car_everywhere, validate_plate, validate_vin
from modules.ip import search_ip_everywhere, validate_ip
from modules.domain import search_domain_everywhere, validate_domain
from modules.crypto import search_crypto_everywhere, detect_crypto_address
from modules.geo import search_geo_everywhere, validate_coords
from modules.exif import search_exif_everywhere

__all__ = [
    "search_phone_everywhere", "validate_phone",
    "search_username", "format_username_report", "validate_username",
    "search_email_everywhere", "validate_email",
    "search_name_everywhere", "validate_name",
    "search_car_everywhere", "validate_plate", "validate_vin",
    "search_ip_everywhere", "validate_ip",
    "search_domain_everywhere", "validate_domain",
    "search_crypto_everywhere", "detect_crypto_address",
    "search_geo_everywhere", "validate_coords",
    "search_exif_everywhere",
]

"""OSINT модули."""

from modules.phone import search_phone_everywhere, validate_phone
from modules.username import search_username, format_username_report, validate_username
from modules.email import search_email_everywhere, validate_email
from modules.name import search_name_everywhere, validate_name
from modules.car import search_car_everywhere, validate_plate, validate_vin
from modules.image import format_image_report

__all__ = [
    "search_phone_everywhere", "validate_phone",
    "search_username", "format_username_report", "validate_username",
    "search_email_everywhere", "validate_email",
    "search_name_everywhere", "validate_name",
    "search_car_everywhere", "validate_plate", "validate_vin",
    "format_image_report",
]

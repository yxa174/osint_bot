"""Модули OSINT поиска."""

from modules.phone import format_phone_report, validate_phone, check_phone_api
from modules.username import search_username, format_username_report, validate_username
from modules.email import format_email_report, validate_email, check_email_breaches
from modules.name import format_name_report, validate_name
from modules.image import format_image_report, generate_image_search_links
from modules.car import format_car_report, validate_plate, validate_vin

__all__ = [
    "format_phone_report", "validate_phone", "check_phone_api",
    "search_username", "format_username_report", "validate_username",
    "format_email_report", "validate_email", "check_email_breaches",
    "format_name_report", "validate_name",
    "format_image_report", "generate_image_search_links",
    "format_car_report", "validate_plate", "validate_vin",
]

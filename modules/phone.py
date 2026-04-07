"""Модуль для поиска информации по номеру телефона."""

import re
import logging

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False

log = logging.getLogger("OSINTBot")


def validate_phone(text: str) -> str | None:
    """Извлекает и валидирует номер телефона из текста."""
    digits = re.sub(r"[^\d+]", "", text)
    if len(digits) < 10:
        return None
    return digits


def parse_phone(phone_raw: str) -> dict:
    """Парсит номер телефона и возвращает информацию."""
    result = {
        "valid": False,
        "formatted": phone_raw,
        "country": "Не определено",
        "region": "Не определено",
        "carrier": "Не определено",
        "type": "Не определено",
        "timezone": "Не определено",
        "international": phone_raw,
    }

    if not HAS_PHONENUMBERS:
        result["error"] = "Библиотека phonenumbers не установлена"
        return result

    try:
        parsed = phonenumbers.parse(phone_raw, None)
        if not phonenumbers.is_valid_number(parsed):
            result["error"] = "Недействительный номер телефона"
            return result

        result["valid"] = True
        result["formatted"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        result["international"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        result["country"] = geocoder.description_for_number(parsed, "ru") or "Не определено"
        result["region"] = geocoder.description_for_number(parsed, "ru") or "Не определено"

        carrier_name = carrier.name_for_number(parsed, "ru")
        result["carrier"] = carrier_name if carrier_name else "Не определено"

        num_type = phonenumbers.number_type(parsed)
        type_map = {
            phonenumbers.PhoneNumberType.MOBILE: "Мобильный",
            phonenumbers.PhoneNumberType.FIXED_LINE: "Стационарный",
            phonenumbers.PhoneNumberType.TOLL_FREE: "Бесплатный",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "Платный",
            phonenumbers.PhoneNumberType.VOIP: "VoIP",
        }
        result["type"] = type_map.get(num_type, "Не определено")

        tz = timezone.time_zones_for_number(parsed)
        result["timezone"] = ", ".join(tz) if tz else "Не определено"

    except phonenumbers.NumberParseException as e:
        result["error"] = f"Ошибка парсинга: {e}"
    except Exception as e:
        log.error(f"Ошибка при парсинге телефона: {e}")
        result["error"] = str(e)

    return result


def get_messenger_info(phone: str) -> dict:
    """Возвращает информацию о привязке номера к мессенджерам."""
    digits = re.sub(r"[^\d]", phone)

    info = {
        "telegram": f"tg://resolve?phone={digits}" if len(digits) >= 11 else "Недоступно",
        "whatsapp": f"https://wa.me/{digits}" if len(digits) >= 11 else "Недоступно",
        "viber": f"viber://chat?number=%2B{digits}" if len(digits) >= 11 else "Недоступно",
    }
    return info


def format_phone_report(phone_raw: str) -> str:
    """Формирует полный отчёт по номеру телефона."""
    phone = validate_phone(phone_raw)
    if not phone:
        return "❌ Не удалось распознать номер телефона.\n\nУбедитесь, что номер содержит минимум 10 цифр."

    data = parse_phone(phone)
    messengers = get_messenger_info(phone)

    report = f"📱 <b>Поиск по номеру телефона</b>\n\n"
    report += f"📞 <b>Номер:</b> <code>{data.get('international', phone)}</code>\n"
    report += f"🌍 <b>Страна:</b> {data.get('country')}\n"
    report += f"📡 <b>Оператор:</b> {data.get('carrier')}\n"
    report += f"📋 <b>Тип:</b> {data.get('type')}\n"
    report += f"🕐 <b>Часовой пояс:</b> {data.get('timezone')}\n"

    if data.get("error"):
        report += f"\n⚠️ <b>Ошибка:</b> {data['error']}\n"

    report += f"\n🔗 <b>Мессенджеры:</b>\n"
    report += f"• Telegram: {messengers['telegram']}\n"
    report += f"• WhatsApp: {messengers['whatsapp']}\n"
    report += f"• Viber: {messengers['viber']}\n"

    return report

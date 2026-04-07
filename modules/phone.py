"""Модуль для поиска информации по номеру телефона."""

import re
import logging
from urllib.parse import quote

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False

log = logging.getLogger("OSINTBot")

# Регионы РФ по первым цифрам после +7
RU_REGIONS = {
    "900": "Не определено (мобильный)",
    "901": "Не определено (мобильный)",
    "902": "Не определено (мобильный)",
    "903": "Москва и МО",
    "904": "Свердловская обл.",
    "905": "Москва и МО",
    "906": "Не определено (мобильный)",
    "908": "Ростовская обл.",
    "909": "Москва и МО",
    "910": "Центральный ФО",
    "911": "СЗФО",
    "912": "Урал",
    "913": "Сибирь",
    "914": "Дальний Восток",
    "915": "Центральный ФО",
    "916": "Москва и МО",
    "917": "Поволжье",
    "918": "Южный ФО",
    "919": "Поволжье",
    "920": "Центральный ФО",
    "921": "СЗФО",
    "922": "Урал",
    "923": "Сибирь",
    "924": "Дальний Восток",
    "925": "Москва и МО",
    "926": "Москва и МО",
    "927": "Поволжье",
    "928": "Южный ФО",
    "929": "Москва и МО",
    "930": "Центральный ФО",
    "931": "СЗФО",
    "932": "Урал",
    "933": "Не определено (мобильный)",
    "934": "Дальний Восток",
    "936": "Москва и МО",
    "937": "Поволжье",
    "938": "Южный ФО",
    "939": "Москва и МО",
    "949": "Центральный ФО",
    "950": "Урал / Сибирь",
    "951": "Не определено (мобильный)",
    "952": "СЗФО / Урал",
    "953": "Сибирь",
    "958": "Не определено (мобильный)",
    "960": "Центральный ФО",
    "961": "Южный ФО",
    "962": "Центральный ФО",
    "963": "Москва и МО",
    "964": "Сибирь",
    "965": "Москва и МО",
    "966": "Москва и МО",
    "967": "Москва и МО",
    "968": "Москва и МО",
    "969": "Москва и МО",
    "977": "Москва и МО",
    "978": "Крым",
    "980": "Центральный ФО",
    "981": "СЗФО",
    "982": "Урал",
    "983": "Сибирь",
    "984": "Не определено",
    "985": "Москва и МО",
    "987": "Поволжье",
    "988": "Южный ФО",
    "989": "Южный ФО",
    "991": "Центральный ФО",
    "993": "Центральный ФО",
    "995": "Южный ФО",
    "996": "Центральный ФО",
    "997": "Москва и МО",
    "999": "Москва и МО",
}


def validate_phone(text: str) -> str | None:
    """Извлекает и валидирует номер телефона из текста."""
    if not text or not isinstance(text, str):
        return None
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
        "country_code": "Не определено",
        "region": "Не определено",
        "carrier": "Не определено",
        "type": "Не определено",
        "timezone": "Не определено",
        "international": phone_raw,
        "national": phone_raw,
        "possible": False,
        "phone_type_ru": "Не определено",
    }

    if not HAS_PHONENUMBERS:
        result["error"] = "Библиотека phonenumbers не установлена"
        return result

    try:
        parsed = phonenumbers.parse(phone_raw, None)

        result["possible"] = phonenumbers.is_possible_number(parsed)
        result["valid"] = phonenumbers.is_valid_number(parsed)

        result["national"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        result["international"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        result["e164"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

        country_code = phonenumbers.region_code_for_number(parsed)
        result["country_code"] = country_code or "Не определено"

        result["country"] = geocoder.country_name_for_number(parsed, "ru") or "Не определено"
        result["region"] = geocoder.description_for_number(parsed, "ru") or "Не определено"

        carrier_name = carrier.name_for_number(parsed, "ru")
        result["carrier"] = carrier_name if carrier_name else "Не определено"

        num_type = phonenumbers.number_type(parsed)
        type_map = {
            phonenumbers.PhoneNumberType.MOBILE: "Мобильный",
            phonenumbers.PhoneNumberType.FIXED_LINE: "Стационарный",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Мобильный/Стационарный",
            phonenumbers.PhoneNumberType.TOLL_FREE: "Бесплатный (800)",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "Платный",
            phonenumbers.PhoneNumberType.SHARED_COST: "Разделённая стоимость",
            phonenumbers.PhoneNumberType.VOIP: "VoIP (виртуальный)",
            phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Персональный",
            phonenumbers.PhoneNumberType.PAGER: "Пейджер",
            phonenumbers.PhoneNumberType.UAN: "Корпоративный (UAN)",
        }
        phone_type = type_map.get(num_type, "Не определено")
        result["type"] = phone_type

        # Определяем регион РФ по DEF-коду
        if country_code == "RU":
            digits_only = re.sub(r"\D", "", phone_raw)
            # Берём 3 цифры после +7
            if len(digits_only) >= 4:
                def_code = digits_only[1:4]  # 999, 926, etc.
                result["region"] = RU_REGIONS.get(def_code, f"Код DEF: {def_code}")

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
    digits = re.sub(r"[^\d]", "", phone)

    info = {
        "telegram": f"https://t.me/+{digits}",
        "wa_link": f"https://wa.me/{digits}",
        "viber": f"viber://chat?number=%2B{digits}",
        "imo": f"https://imo.im/phone/{digits}",
    }
    return info


def generate_search_links(phone: str) -> list[dict]:
    """Генерирует ссылки для ручного поиска по номеру."""
    digits = re.sub(r"[^\d]", "", phone)
    encoded = quote(digits, safe="")

    return [
        {"name": "Google", "url": f"https://www.google.com/search?q={encoded}", "icon": "🔍"},
        {"name": "Yandex", "url": f"https://yandex.ru/search/?text={encoded}", "icon": "🟡"},
        {"name": "GetContact", "url": "https://www.getcontact.com/", "icon": "📱"},
        {"name": "NumVerify", "url": "https://numverify.com/", "icon": "✅"},
        {"name": "Truecaller", "url": f"https://www.truecaller.com/search/ru/{encoded}", "icon": "📞"},
        {"name": "PhoneBook", "url": f"https://phonebook.cz/?query={encoded}", "icon": "📖"},
        {"name": "2GIS", "url": f"https://2gis.ru/search?query={encoded}", "icon": "🗺"},
        {"name": "Авито", "url": f"https://www.avito.ru/?q={encoded}", "icon": "🛒"},
        {"name": "Сбербанк (перевод)", "url": f"https://www.sberbank.ru/", "icon": "🏦"},
        {"name": "Tinkoff (перевод)", "url": f"https://www.tinkoff.ru/", "icon": "💳"},
    ]


def format_phone_report(phone_raw: str) -> str:
    """Формирует полный отчёт по номеру телефона."""
    phone = validate_phone(phone_raw)
    if not phone:
        return "❌ Не удалось распознать номер телефона.\n\nУбедитесь, что номер содержит минимум 10 цифр."

    data = parse_phone(phone)
    messengers = get_messenger_info(phone)
    links = generate_search_links(phone)

    report = f"📱 <b>Поиск по номеру телефона</b>\n\n"
    report += f"📞 <b>Номер:</b> <code>{data.get('international', phone)}</code>\n"
    report += f"📋 <b>Национальный формат:</b> {data.get('national', phone)}\n"

    if data.get("e164"):
        report += f"📝 <b>E164:</b> <code>{data['e164']}</code>\n"

    report += f"🌍 <b>Страна:</b> {data.get('country')} ({data.get('country_code')})\n"
    report += f"📍 <b>Регион:</b> {data.get('region')}\n"
    report += f"📡 <b>Оператор:</b> {data.get('carrier')}\n"
    report += f"📋 <b>Тип:</b> {data.get('type')}\n"

    if data.get("timezone") and data["timezone"] != "Не определено":
        report += f"🕐 <b>Часовой пояс:</b> {data.get('timezone')}\n"

    if data.get("possible"):
        status = "✅ Да" if data.get("valid") else "⚠️ Возможный, но недействительный"
        report += f"✅ <b>Действительный:</b> {status}\n"

    if data.get("error"):
        report += f"\n⚠️ <b>Ошибка:</b> {data['error']}\n"

    # Мессенджеры
    report += f"\n🔗 <b>Мессенджеры:</b>\n"
    report += f"• Telegram: <a href=\"{messengers['telegram']}\">Открыть</a>\n"
    report += f"• WhatsApp: <a href=\"{messengers['wa_link']}\">Открыть</a>\n"
    report += f"• Viber: <a href=\"{messengers['viber']}\">Открыть</a>\n"
    report += f"• IMO: <a href=\"{messengers['imo']}\">Открыть</a>\n"

    # Ссылки для ручного поиска
    report += f"\n🔎 <b>Ручной поиск:</b>\n"
    for link in links:
        report += f"• {link['icon']} <a href=\"{link['url']}\">{link['name']}</a>\n"

    report += "\n💡 <i>Используйте ссылки для поиска дополнительной информации</i>"

    return report

"""Модуль для поиска информации по номеру телефона — с реальными API."""

import re
import logging
import json
import asyncio
from urllib.parse import quote

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False

log = logging.getLogger("OSINTBot")

# Регионы РФ по DEF-коду
RU_REGIONS = {
    "900": "Мобильный", "901": "Мобильный", "902": "Мобильный",
    "903": "Москва и МО (Beeline)", "904": "Свердловская обл.",
    "905": "Москва и МО (Beeline)", "906": "Мобильный (Beeline)",
    "908": "Ростовская обл.", "909": "Москва и МО (Beeline)",
    "910": "Центральный ФО (MTS)", "911": "СЗФО (MTS)",
    "912": "Урал (MTS)", "913": "Сибирь (MTS)",
    "914": "Дальний Восток (MTS)", "915": "Центральный ФО (MTS)",
    "916": "Москва и МО (MTS)", "917": "Поволжье (MTS)",
    "918": "Южный ФО (MTS)", "919": "Поволжье (MTS)",
    "920": "Центральный ФО (MegaFon)", "921": "СЗФО (MegaFon)",
    "922": "Урал (MegaFon)", "923": "Сибирь (MegaFon)",
    "924": "Дальний Восток (MegaFon)", "925": "Москва и МО (MegaFon)",
    "926": "Москва и МО (MegaFon)", "927": "Поволжье (MegaFon)",
    "928": "Южный ФО (MegaFon)", "929": "Москва и МО (MegaFon)",
    "930": "Центральный ФО", "931": "СЗФО", "932": "Урал",
    "933": "Мобильный", "934": "Дальний Восток",
    "936": "Москва и МО (MegaFon)", "937": "Поволжье (MegaFon)",
    "938": "Южный ФО (MegaFon)", "939": "Москва и МО",
    "949": "Центральный ФО", "950": "Урал/Сибирь (Tele2)",
    "951": "Мобильный (Tele2)", "952": "СЗФО/Урал (Tele2)",
    "953": "Сибирь (Tele2)", "958": "Мобильный (Tele2)",
    "960": "Центральный ФО (Tele2)", "961": "Южный ФО (Tele2)",
    "962": "Центральный ФО (Tele2)", "963": "Москва и МО (Tele2)",
    "964": "Сибирь (Tele2)", "965": "Москва и МО (Tele2)",
    "966": "Москва и МО (Tele2)", "967": "Москва и МО (Tele2)",
    "968": "Москва и МО (Tele2)", "969": "Москва и МО (Tele2)",
    "977": "Москва и МО (MegaFon)", "978": "Крым",
    "980": "Центральный ФО (MTS)", "981": "СЗФО (MTS)",
    "982": "Урал (MTS)", "983": "Сибирь (MTS)",
    "984": "Не определено", "985": "Москва и МО (MTS)",
    "987": "Поволжье (MTS)", "988": "Южный ФО (MTS)",
    "989": "Южный ФО (MTS)", "991": "Центральный ФО (Tele2)",
    "993": "Центральный ФО (Tele2)", "995": "Южный ФО (Tele2)",
    "996": "Центральный ФО (Tele2)", "997": "Москва и МО (Yota)",
    "999": "Москва и МО (Yota)",
}

OPERATORS_BY_DEF = {
    "903": "Beeline", "905": "Beeline", "906": "Beeline", "909": "Beeline",
    "926": "MegaFon", "925": "MegaFon", "929": "MegaFon", "977": "MegaFon",
    "936": "MegaFon", "937": "MegaFon", "938": "MegaFon", "928": "MegaFon",
    "920": "MegaFon", "921": "MegaFon", "922": "MegaFon", "923": "MegaFon",
    "924": "MegaFon", "927": "MegaFon",
    "910": "MTS", "911": "MTS", "912": "MTS", "913": "MTS",
    "914": "MTS", "915": "MTS", "916": "MTS", "917": "MTS",
    "918": "MTS", "919": "MTS", "980": "MTS", "981": "MTS",
    "982": "MTS", "983": "MTS", "985": "MTS", "988": "MTS",
    "989": "MTS", "987": "MTS",
    "950": "Tele2", "951": "Tele2", "952": "Tele2", "953": "Tele2",
    "958": "Tele2", "960": "Tele2", "961": "Tele2", "962": "Tele2",
    "963": "Tele2", "964": "Tele2", "965": "Tele2", "966": "Tele2",
    "967": "Tele2", "968": "Tele2", "969": "Tele2", "991": "Tele2",
    "993": "Tele2", "995": "Tele2", "996": "Tele2",
    "999": "Yota", "997": "Yota", "992": "Yota", "995": "Yota",
}


def validate_phone(text: str) -> str | None:
    """Извлекает номер телефона."""
    if not text or not isinstance(text, str):
        return None
    digits = re.sub(r"[^\d+]", "", text)
    if len(digits) < 10:
        return None
    return digits


def parse_phone_local(phone_raw: str) -> dict:
    """Локальный парсинг номера (без API)."""
    result = {
        "valid": False, "possible": False,
        "international": phone_raw, "national": phone_raw,
        "e164": phone_raw, "country": "Не определено",
        "country_code": "Не определено", "region": "Не определено",
        "carrier": "Не определено", "type": "Не определено",
        "timezone": "Не определено", "def_code": None,
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

        cc = phonenumbers.region_code_for_number(parsed)
        result["country_code"] = cc or "Не определено"
        result["country"] = geocoder.country_name_for_number(parsed, "ru") or "Не определено"
        result["region"] = geocoder.description_for_number(parsed, "ru") or "Не определено"

        carr = carrier.name_for_number(parsed, "ru")
        if carr:
            result["carrier"] = carr

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
        result["type"] = type_map.get(phonenumbers.number_type(parsed), "Не определено")

        # РФ регион по DEF-коду
        if cc == "RU":
            digits_only = re.sub(r"\D", "", phone_raw)
            if len(digits_only) >= 4:
                def_code = digits_only[1:4]
                result["def_code"] = def_code
                result["region"] = RU_REGIONS.get(def_code, f"Код DEF: {def_code}")
                if not carr:
                    result["carrier"] = OPERATORS_BY_DEF.get(def_code, "Не определено")

        tz = timezone.time_zones_for_number(parsed)
        result["timezone"] = ", ".join(tz) if tz else "Не определено"

    except phonenumbers.NumberParseException as e:
        result["error"] = f"Ошибка парсинга: {e}"
    except Exception as e:
        log.error(f"Ошибка при парсинге телефона: {e}")
        result["error"] = str(e)

    return result


async def query_phone_apis(phone: str, e164: str) -> dict:
    """Запросы к реальным API для получения данных о номере."""
    import config
    api_results = {}

    # Abstract API — валидация и определение оператора
    if config.ABSTRACT_PHONE_API_KEY:
        try:
            import httpx
            url = f"https://phonevalidation.abstractapi.com/v1/validate_phone"
            params = {"api_key": config.ABSTRACT_PHONE_API_KEY, "phone": e164}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    api_results["abstract_api"] = {
                        "valid": data.get("is_valid", False),
                        "country": data.get("country", ""),
                        "location": data.get("location", ""),
                        "carrier": data.get("carrier", ""),
                        "line_type": data.get("line_type", ""),
                        "type": data.get("type", ""),
                        "formatted": data.get("formatted", ""),
                    }
        except Exception as e:
            log.debug(f"Abstract API error: {e}")

    # NumVerify — определение оператора и локации
    if config.NUMVERIFY_API_KEY:
        try:
            import httpx
            url = "http://apilayer.net/api/validate"
            params = {"access_key": config.NUMVERIFY_API_KEY, "number": e164, "format": "1"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if not data.get("error"):
                        api_results["numverify"] = {
                            "valid": data.get("valid", False),
                            "country": data.get("country_name", ""),
                            "location": data.get("location", ""),
                            "carrier": data.get("carrier", ""),
                            "line_type": data.get("line_type", ""),
                            "national_format": data.get("national_format", ""),
                        }
        except Exception as e:
            log.debug(f"NumVerify error: {e}")

    # PhoneBook.cz — поиск в утечках
    try:
        import httpx
        digits_only = re.sub(r"[^\d]", "", phone)
        # PhoneBook.cz ищет по email, но может найти данные по номеру
        url = f"https://phonebook.cz/api"
        # Этот API требует email, пропускаем для телефона
    except Exception:
        pass

    # Numlookup API — бесплатный
    if hasattr(config, 'NUMLOOKUP_API_KEY') and getattr(config, 'NUMLOOKUP_API_KEY', ''):
        try:
            import httpx
            url = f"https://numlookupapi.com/api/validate/{e164}"
            params = {"apikey": config.NUMLOOKUP_API_KEY}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    api_results["numlookup"] = {
                        "valid": data.get("valid", False),
                        "country": data.get("country_name", ""),
                        "carrier": data.get("carrier", ""),
                        "location": data.get("location", ""),
                        "line_type": data.get("line_type", ""),
                    }
        except Exception as e:
            log.debug(f"Numlookup API error: {e}")

    return api_results


async def search_phone_everywhere(phone: str) -> str:
    """Полный поиск по номеру телефона с реальными данными."""
    validated = validate_phone(phone)
    if not validated:
        return "❌ Неверный формат номера.\n\nПример: <code>+79991234567</code>"

    # Локальный парсинг
    local_data = parse_phone_local(validated)

    # API запросы
    e164 = local_data.get("e164", validated)
    api_data = await query_phone_apis(validated, e164)

    # Формируем отчёт
    report = f"📱 <b>Расширенный поиск по номеру</b>\n\n"
    report += f"📞 <b>Международный:</b> <code>{local_data['international']}</code>\n"
    report += f"📋 <b>Национальный:</b> <code>{local_data['national']}</code>\n"
    report += f"📝 <b>E164:</b> <code>{local_data['e164']}</code>\n\n"

    report += f"🌍 <b>Страна:</b> {local_data['country']}"
    if local_data['country_code'] != "Не определено":
        report += f" ({local_data['country_code']})"
    report += "\n"

    report += f"📍 <b>Регион:</b> {local_data['region']}\n"

    # Оператор
    carrier_val = local_data.get("carrier", "Не определено")
    if carrier_val == "Не определено" and local_data.get("def_code"):
        carrier_val = OPERATORS_BY_DEF.get(local_data["def_code"], "Не определено")
    report += f"📡 <b>Оператор:</b> {carrier_val}\n"
    report += f"📋 <b>Тип:</b> {local_data['type']}\n"
    report += f"✅ <b>Действительный:</b> {'Да' if local_data['valid'] else 'Нет'}\n"

    if local_data.get("timezone") and local_data["timezone"] != "Не определено":
        report += f"🕐 <b>Часовой пояс:</b> {local_data['timezone']}\n"

    # Данные из API
    if api_data:
        for api_name, api_info in api_data.items():
            report += f"\n🔌 <b>{api_name.replace('_', ' ').title()}:</b>\n"
            if api_info.get("carrier") and api_info["carrier"] != local_data["carrier"]:
                report += f"  📡 Оператор: {api_info['carrier']}\n"
            if api_info.get("location"):
                report += f"  📍 Локация: {api_info['location']}\n"
            if api_info.get("line_type"):
                report += f"  📋 Тип линии: {api_info['line_type']}\n"
            if api_info.get("country") and api_info["country"] != local_data["country"]:
                report += f"  🌍 Страна: {api_info['country']}\n"
            if api_info.get("formatted"):
                report += f"  📋 Формат: {api_info['formatted']}\n"

    # Мессенджеры
    digits_only = re.sub(r"[^\d]", "", validated)
    report += f"\n🔗 <b>Мессенджеры (прямые ссылки):</b>\n"
    report += f"• Telegram: <a href=\"https://t.me/+{digits_only}\">Открыть профиль</a>\n"
    report += f"• WhatsApp: <a href=\"https://wa.me/{digits_only}\">Открыть чат</a>\n"
    report += f"• Viber: <a href=\"viber://chat?number=%2B{digits_only}\">Открыть чат</a>\n"
    report += f"• Signal: <a href=\"https://signal.me/#p/+{digits_only}\">Открыть профиль</a>\n"

    report += "\n💡 <i>Данные собраны из открытых источников и API</i>"

    return report

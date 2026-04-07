"""Модуль для поиска информации по номеру телефона — расширенный."""

import re
import logging
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
    "903": "Москва и МО", "904": "Свердловская обл.", "905": "Москва и МО",
    "906": "Мобильный", "908": "Ростовская обл.", "909": "Москва и МО",
    "910": "Центральный ФО", "911": "СЗФО", "912": "Урал", "913": "Сибирь",
    "914": "Дальний Восток", "915": "Центральный ФО", "916": "Москва и МО",
    "917": "Поволжье", "918": "Южный ФО", "919": "Поволжье",
    "920": "Центральный ФО", "921": "СЗФО", "922": "Урал", "923": "Сибирь",
    "924": "Дальний Восток", "925": "Москва и МО", "926": "Москва и МО",
    "927": "Поволжье", "928": "Южный ФО", "929": "Москва и МО",
    "930": "Центральный ФО", "931": "СЗФО", "932": "Урал", "933": "Мобильный",
    "934": "Дальний Восток", "936": "Москва и МО", "937": "Поволжье",
    "938": "Южный ФО", "939": "Москва и МО", "949": "Центральный ФО",
    "950": "Урал / Сибирь", "951": "Мобильный", "952": "СЗФО / Урал",
    "953": "Сибирь", "958": "Мобильный", "960": "Центральный ФО",
    "961": "Южный ФО", "962": "Центральный ФО", "963": "Москва и МО",
    "964": "Сибирь", "965": "Москва и МО", "966": "Москва и МО",
    "967": "Москва и МО", "968": "Москва и МО", "969": "Москва и МО",
    "977": "Москва и МО", "978": "Крым", "980": "Центральный ФО",
    "981": "СЗФО", "982": "Урал", "983": "Сибирь", "984": "Не определено",
    "985": "Москва и МО", "987": "Поволжье", "988": "Южный ФО",
    "989": "Южный ФО", "991": "Центральный ФО", "993": "Центральный ФО",
    "995": "Южный ФО", "996": "Центральный ФО", "997": "Москва и МО",
    "999": "Москва и МО",
}

# Операторы по диапазонам (упрощённо)
OPERATORS = {
    "903": ["Beeline"], "905": ["Beeline"], "906": ["Beeline"],
    "909": ["Beeline"], "926": ["MegaFon"], "925": ["MegaFon"],
    "929": ["MegaFon"], "977": ["MegaFon"], "936": ["MegaFon"],
    "937": ["MegaFon"], "938": ["MegaFon"], "928": ["MegaFon"],
    "910": ["MTS"], "911": ["MTS"], "912": ["MTS"], "913": ["MTS"],
    "914": ["MTS"], "915": ["MTS"], "916": ["MTS"], "917": ["MTS"],
    "918": ["MTS"], "919": ["MTS"], "980": ["MTS"], "981": ["MTS"],
    "982": ["MTS"], "983": ["MTS"], "985": ["MTS"], "988": ["MTS"],
    "989": ["MTS"], "987": ["MTS"],
    "950": ["Tele2"], "951": ["Tele2"], "952": ["Tele2"], "953": ["Tele2"],
    "958": ["Tele2"], "960": ["Tele2"], "961": ["Tele2"], "962": ["Tele2"],
    "963": ["Tele2"], "964": ["Tele2"], "965": ["Tele2"], "966": ["Tele2"],
    "967": ["Tele2"], "968": ["Tele2"], "969": ["Tele2"], "991": ["Tele2"],
    "993": ["Tele2"], "995": ["Tele2"], "996": ["Tele2"],
    "999": ["Yota"], "997": ["Yota"], "992": ["Yota"],
}


def validate_phone(text: str) -> str | None:
    """Извлекает и валидирует номер телефона."""
    if not text or not isinstance(text, str):
        return None
    digits = re.sub(r"[^\d+]", "", text)
    if len(digits) < 10:
        return None
    return digits


def parse_phone(phone_raw: str) -> dict:
    """Расширенный парсинг номера телефона."""
    result = {
        "valid": False, "possible": False,
        "formatted": phone_raw, "international": phone_raw,
        "national": phone_raw, "e164": phone_raw,
        "country": "Не определено", "country_code": "Не определено",
        "region": "Не определено", "carrier": "Не определено",
        "type": "Не определено", "timezone": "Не определено",
        "is_ru": False, "def_code": None, "operator_guess": None,
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
        result["is_ru"] = cc == "RU"
        result["region"] = geocoder.description_for_number(parsed, "ru") or "Не определено"

        carr = carrier.name_for_number(parsed, "ru")
        result["carrier"] = carr if carr else "Не определено"

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

        # РФ: определяем регион и оператора по DEF-коду
        if cc == "RU":
            digits_only = re.sub(r"\D", "", phone_raw)
            if len(digits_only) >= 4:
                def_code = digits_only[1:4]
                result["def_code"] = def_code
                result["region"] = RU_REGIONS.get(def_code, f"Код DEF: {def_code}")
                result["operator_guess"] = OPERATORS.get(def_code, [])

        tz = timezone.time_zones_for_number(parsed)
        result["timezone"] = ", ".join(tz) if tz else "Не определено"

    except phonenumbers.NumberParseException as e:
        result["error"] = f"Ошибка парсинга: {e}"
    except Exception as e:
        log.error(f"Ошибка при парсинге телефона: {e}")
        result["error"] = str(e)

    return result


def get_messenger_links(phone: str) -> dict:
    """Ссылки на мессенджеры."""
    digits = re.sub(r"[^\d]", "", phone)
    return {
        "Telegram": f"https://t.me/+{digits}",
        "WhatsApp": f"https://wa.me/{digits}",
        "Viber": f"viber://chat?number=%2B{digits}",
        "IMO": f"https://imo.im/phone/{digits}",
        "Signal": f"https://signal.me/#p/+{digits}",
        "Threema": f"threema://compose?phone=+{digits}",
    }


def get_search_links(phone: str) -> dict:
    """Ссылки для ручного поиска."""
    digits = re.sub(r"[^\d]", "", phone)
    encoded = quote(digits, safe="")
    return {
        "Поисковики": {
            "Google": f"https://www.google.com/search?q={encoded}",
            "Yandex": f"https://yandex.ru/search/?text={encoded}",
            "Bing": f"https://www.bing.com/search?q={encoded}",
            "DuckDuckGo": f"https://duckduckgo.com/?q={encoded}",
        },
        "Определители": {
            "Truecaller": f"https://www.truecaller.com/search/ru/{encoded}",
            "GetContact": "https://www.getcontact.com/",
            "NumVerify": "https://numverify.com/",
            "PhoneBook.cz": f"https://phonebook.cz/?query={encoded}",
            "CallerID": f"https://callerid.ru/search/?q={encoded}",
        },
        "Доски объявлений": {
            "Авито": f"https://www.avito.ru/?q={encoded}",
            "Юла": f"https://youla.ru/?q={encoded}",
            "Из рук в руки": f"https://www.irr.ru/?q={encoded}",
        },
        "Карты и справочники": {
            "2GIS": f"https://2gis.ru/search?query={encoded}",
            "Яндекс.Карты": f"https://yandex.ru/maps/?pt={encoded}",
            "Zoon": f"https://zoon.ru/?s={encoded}",
            "OrgPage": f"https://www.orgpage.ru/search/?q={encoded}",
        },
        "Банки (проверка имени)": {
            "Сбербанк": "https://www.sberbank.ru/ru/person/dl_offices",
            "Тинькофф": "https://www.tinkoff.ru/",
            "Альфа-Банк": "https://alfabank.ru/",
        },
        "Соцсети": {
            "VK": f"https://vk.com/search?c%5Bq%5D={encoded}&c%5Bsection%5D=auto",
            "OK": f"https://ok.ru/search?st.cmd=sFriendSearch&st.query={encoded}",
        },
    }


async def check_phone_api(phone: str) -> dict:
    """Проверка через внешние API (опционально)."""
    result = {
        "abstract_api": None,
        "numverify": None,
        "error": None,
    }

    import config

    # Abstract API — определение оператора и локации
    if config.ABSTRACT_PHONE_API_KEY:
        try:
            import httpx
            url = f"https://phonevalidation.abstractapi.com/v1/validate_phone?api_key={config.ABSTRACT_PHONE_API_KEY}&phone={phone}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    result["abstract_api"] = resp.json()
        except Exception as e:
            log.debug(f"Abstract API error: {e}")

    # NumVerify
    if config.NUMVERIFY_API_KEY:
        try:
            import httpx
            url = f"http://apilayer.net/api/validate?access_key={config.NUMVERIFY_API_KEY}&number={phone}&format=1"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    result["numverify"] = resp.json()
        except Exception as e:
            log.debug(f"NumVerify error: {e}")

    return result


def format_phone_report(phone_raw: str, api_data: dict | None = None) -> str:
    """Формирует расширенный отчёт по номеру телефона."""
    phone = validate_phone(phone_raw)
    if not phone:
        return "❌ Не удалось распознать номер.\n\nПример: <code>+79991234567</code>"

    data = parse_phone(phone)
    messengers = get_messenger_links(phone)
    search_links = get_search_links(phone)

    report = f"📱 <b>Расширенный поиск по номеру</b>\n\n"
    report += f"📞 <b>Международный:</b> <code>{data['international']}</code>\n"
    report += f"📋 <b>Национальный:</b> <code>{data['national']}</code>\n"
    report += f"📝 <b>E164:</b> <code>{data['e164']}</code>\n\n"

    report += f"🌍 <b>Страна:</b> {data['country']} ({data['country_code']})\n"
    report += f"📍 <b>Регион:</b> {data['region']}\n"

    if data.get("def_code"):
        report += f"🔢 <b>DEF-код:</b> {data['def_code']}\n"

    # Оператор
    carr = data.get("carrier", "Не определено")
    guess = data.get("operator_guess", [])
    if carr and carr != "Не определено":
        report += f"📡 <b>Оператор:</b> {carr}\n"
    elif guess:
        report += f"📡 <b>Возможный оператор:</b> {', '.join(guess)}\n"
    else:
        report += f"📡 <b>Оператор:</b> Не определено\n"

    report += f"📋 <b>Тип:</b> {data['type']}\n"
    report += f"✅ <b>Действительный:</b> {'Да' if data['valid'] else 'Нет'}\n"
    report += f"🔮 <b>Возможный:</b> {'Да' if data['possible'] else 'Нет'}\n"

    if data.get("timezone") and data["timezone"] != "Не определено":
        report += f"🕐 <b>Часовой пояс:</b> {data['timezone']}\n"

    # API данные
    if api_data:
        aa = api_data.get("abstract_api")
        if aa:
            report += f"\n🔌 <b>Abstract API:</b>\n"
            if aa.get("location"):
                report += f"  📍 Локация: {aa['location']}\n"
            if aa.get("carrier"):
                report += f"  📡 Оператор: {aa['carrier']}\n"
            if aa.get("line_type"):
                report += f"  📋 Тип линии: {aa['line_type']}\n"

        nv = api_data.get("numverify")
        if nv:
            report += f"\n🔌 <b>NumVerify:</b>\n"
            if nv.get("location"):
                report += f"  📍 Локация: {nv['location']}\n"
            if nv.get("carrier"):
                report += f"  📡 Оператор: {nv['carrier']}\n"
            if nv.get("line_type"):
                report += f"  📋 Тип: {nv['line_type']}\n"
            if nv.get("country_name"):
                report += f"  🌍 Страна: {nv['country_name']}\n"

    # Мессенджеры
    report += f"\n🔗 <b>Мессенджеры:</b>\n"
    for name, url in messengers.items():
        report += f"• <a href=\"{url}\">{name}</a>\n"

    # Ссылки для поиска
    report += f"\n🔎 <b>Сервисы для поиска:</b>\n"
    for category, links in search_links.items():
        report += f"\n<b>{category}:</b>\n"
        for name, url in links.items():
            report += f"• <a href=\"{url}\">{name}</a>\n"

    report += "\n💡 <i>Нажмите на ссылку для поиска дополнительной информации</i>"

    return report

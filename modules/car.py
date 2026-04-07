"""Модуль для поиска по автомобилю — с реальными API."""

import re
import logging
import asyncio
from urllib.parse import quote

log = logging.getLogger("OSINTBot")


def validate_plate(text: str) -> str | None:
    """Валидирует госномер РФ."""
    text = text.strip().upper()
    pattern = r"^([АВЕКМНОРСТУХ]\d{3}[А-Я]{2})(\d{2,3})$"
    if re.match(pattern, text.replace(" ", "")):
        return text.replace(" ", "")
    return None


def validate_vin(text: str) -> str | None:
    """Валидирует VIN."""
    text = text.strip().upper()
    if re.match(r"^[A-HJ-NPR-Z0-9]{17}$", text):
        return text
    return None


def decode_vin(vin: str) -> dict:
    """Декодирование VIN — извлекает базовую информацию."""
    result = {
        "country": "", "manufacturer": "", "year": "",
        "plant": "", "serial": "",
    }

    # Страна производства (1-й символ)
    country_map = {
        "1": "США", "2": "Канада", "3": "Мексика",
        "4": "США", "5": "США", "6": "Австралия",
        "J": "Япония", "K": "Корея", "L": "Китай",
        "S": "Великобритания", "V": "Франция/Испания",
        "W": "Германия", "Y": "Швеция/Финляндия",
        "Z": "Италия", "X": "Россия/Нидерланды",
    }
    result["country"] = country_map.get(vin[0], "Не определено")

    # Производитель (2-3 символы)
    mfr = vin[1:3]
    mfr_map = {
        "VA": "Audi", "VW": "Volkswagen", "WB": "BMW", "WDB": "Mercedes",
        "W0": "Opel", "WF": "Ford (Европа)", "VF": "Peugeot/Citroen/Renault",
        "JT": "Toyota (Япония)", "JH": "Honda", "JF": "Subaru",
        "KM": "Hyundai", "KN": "Kia", "JN": "Nissan",
        "1G": "General Motors", "1F": "Ford (США)", "2T": "Toyota (Канада)",
        "3V": "Volkswagen (Мексика)", "XW": "Volkswagen (Россия)",
        "X7": "BMW (Россия)", "X4X": "ГАЗ", "XWK": "КамАЗ",
    }
    result["manufacturer"] = mfr_map.get(mfr, mfr_map.get(vin[1:4], "Не определено"))

    # Год выпуска (10-й символ)
    year_map = {
        "A": "2010", "B": "2011", "C": "2012", "D": "2013", "E": "2014",
        "F": "2015", "G": "2016", "H": "2017", "J": "2018", "K": "2019",
        "L": "2020", "M": "2021", "N": "2022", "P": "2023", "R": "2024",
        "S": "2025",
        "Y": "2000", "1": "2001", "2": "2002", "3": "2003", "4": "2004",
        "5": "2005", "6": "2006", "7": "2007", "8": "2008", "9": "2009",
    }
    result["year"] = year_map.get(vin[9], "Не определено")

    # Завод (11-й символ)
    result["plant"] = f"Код завода: {vin[10]}"
    result["serial"] = vin[11:]  # Серийный номер

    return result


async def query_vin_decoder(vin: str) -> dict:
    """Запрос к бесплатному VIN декодеру."""
    result = {}
    try:
        import httpx
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("Results", [])
                # Извлекаем значимые поля
                for item in results:
                    var = item.get("Variable", "")
                    val = item.get("Value", "")
                    if var in ("Make", "Model", "Model Year", "Body Class", "Engine Cylinders",
                               "Engine HP", "Transmission Style", "Drive Type", "Fuel Type Primary",
                               "Vehicle Type", "Plant Country", "Plant City", "Plant Company Name"):
                        if val and val != "null":
                            result[var] = val
    except Exception as e:
        log.debug(f"VIN decoder error: {e}")

    return result


async def search_car_everywhere(plate: str | None = None, vin: str | None = None) -> str:
    """Полный поиск по авто с реальными данными."""
    report = f"🚗 <b>Поиск по автомобилю</b>\n\n"

    vin_data = {}

    if vin:
        report += f"🔑 <b>VIN:</b> <code>{vin}</code>\n\n"

        # Локальное декодирование
        local_vin = decode_vin(vin)
        report += f"🔍 <b>Локальное декодирование:</b>\n"
        report += f"• 🌍 Страна: {local_vin['country']}\n"
        report += f"• 🏭 Производитель: {local_vin['manufacturer']}\n"
        report += f"• 📅 Год: {local_vin['year']}\n"
        report += f"• 🏗 Завод: {local_vin['plant']}\n"
        report += f"• 🔢 Серийный номер: {local_vin['serial']}\n"

        # API запрос к NHTSA
        report += f"\n🔌 <b>NHTSA (VIN Decoder):</b>\n"
        vin_data = await query_vin_decoder(vin)

        if vin_data:
            for key, val in vin_data.items():
                report += f"• {key}: {val}\n"
        else:
            report += f"  ⚠️ Нет данных от NHTSA\n"

    if plate:
        if vin:
            report += "\n"
        report += f"🔢 <b>Госномер:</b> <code>{plate}</code>\n"

        # Парсинг региона из госномера
        import re
        match = re.match(r"[АВЕКМНОРСТУХ]\d{3}[А-Я]{2}(\d{2,3})", plate)
        if match:
            region_code = match.group(1)
            region_map = {
                "01": "Адыгея", "02": "Башкортостан", "03": "Бурятия",
                "10": "Карелия", "11": "Коми", "16": "Татарстан",
                "23": "Краснодарский край", "34": "Волгоградская обл.",
                "36": "Воронежская обл.", "50": "Московская обл.",
                "52": "Нижегородская обл.", "59": "Пермский край",
                "61": "Ростовская обл.", "63": "Самарская обл.",
                "66": "Свердловская обл.", "72": "Тюменская обл.",
                "74": "Челябинская обл.", "77": "Москва",
                "78": "Санкт-Петербург", "86": "ХМАО",
                "90": "Московская обл.", "96": "Свердловская обл.",
                "97": "Москва", "99": "Москва",
            }
            region = region_map.get(region_code, f"Код: {region_code}")
            report += f"📍 <b>Регион регистрации:</b> {region}\n"

    # Рекомендации по проверке
    report += f"\n📋 <b>Рекомендуемые проверки:</b>\n"
    report += f"• 🚨 Розыск и ограничения: гибдд.рф/check/auto\n"
    report += f"• 📜 История регистрации: ГИБДД\n"
    report += f"• 💰 Штрафы: гибдд.рф/check/fines\n"
    report += f"• 🔒 Реестр залогов: reestr-zalogov.ru\n"
    report += f"• 📋 Автотека (полная история): avito.ru/avтотека\n"
    report += f"• 🖼 Фото по номеру: butovo.numbergram.ru\n"
    report += f"• 📊 ДТП и ремонты: автотека\n"

    if vin_data.get("Make") and vin_data.get("Model"):
        make = vin_data["Make"]
        model = vin_data.get("Model", "")
        year = vin_data.get("Model Year", "")
        report += f"\n🔎 <b>Поиск {make} {model} {year}:</b>\n"
        report += f"• Авито: avito.ru/avtomobili\n"
        report += f"• Авто.ру: auto.ru\n"
        report += f"• Дром: auto.drom.ru\n"

    report += "\n\n💡 <i>Данные из открытых источников и API</i>"

    return report

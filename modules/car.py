"""Модуль для поиска по автомобилю (госномер, VIN, марка)."""

import re
import logging
from urllib.parse import quote

log = logging.getLogger("OSINTBot")


def validate_plate(text: str) -> str | None:
    """Валидирует госномер РФ."""
    text = text.strip().upper()
    # Формат: А123БВ77, А123БВ777, А123ВС777
    pattern = r"^([АВЕКМНОРСТУХ]\d{3}[А-Я]{2})(\d{2,3})$"
    if re.match(pattern, text.replace(" ", "")):
        return text.replace(" ", "")
    return None


def validate_vin(text: str) -> str | None:
    """Валидирует VIN номер."""
    text = text.strip().upper()
    if re.match(r"^[A-HJ-NPR-Z0-9]{17}$", text):
        return text
    return None


def generate_car_search_links(plate: str | None = None, vin: str | None = None) -> dict:
    """Генерирует ссылки для поиска по авто."""
    links = {
        "Проверка истории": {
            "ГИБДД.РФ": "https://гибдд.рф/check/auto",
            "Автотека (Авито)": "https://www.avito.ru/avtотека",
            "ПроАвто": "https://www.proauto.ru/",
            "Автокод": "https://avtokod.mos.ru/",
        },
        "VIN-проверка": {
            "VIN decoder": "https://vindecoderz.com/",
            "AutoDNA": "https://www.autodna.ru/vin-decoder",
            "CARFAX": "https://www.carfax.eu/",
            "VINinfo": "https://vininfo.ru/",
        },
        "Розыск и штрафы": {
            "Штрафы ГИБДД": "https://гибдд.рф/check/fines",
            "Розыск ТС": "https://гибдд.рф/check/auto",
            "Реестр залогов": "https://www.reestr-zalogov.ru/",
            "Реестр ОСАГО (РСА)": "https://dkbm-web.autoins.ru/dkbm.htm",
        },
        "Доски объявлений": {
            "Авито Авто": "https://www.avito.ru/rossiya/avtomobili",
            "Авто.ру": "https://auto.ru/",
            "Дром": "https://auto.drom.ru/",
            "Auto.ru": "https://auto.ru/search/",
        },
        "Фото авто": {
            "Номерограм": "https://butovo.numbergram.ru/",
            "РосЯма (фото)": "https://rosyama.ru/",
            "FSSP (по владельцу)": "https://fssp.gov.ru/iss/ip",
        },
    }

    if plate:
        plate_encoded = quote(plate, safe="")
        links["Поисковики"] = {
            "Google": f"https://www.google.com/search?q={plate_encoded}",
            "Yandex": f"https://yandex.ru/search/?text={plate_encoded}",
            "Номерограм": f"https://butovo.numbergram.ru/search?query={plate_encoded}",
        }
        links["Доски объявлений"].update({
            "Авито (по номеру)": f"https://www.avito.ru/rossiya/avtomobili?q={plate_encoded}",
            "Авто.ру (по номеру)": f"https://auto.ru/search/?query={plate_encoded}",
        })

    if vin:
        vin_encoded = quote(vin, safe="")
        links["VIN-проверка"].update({
            "VIN (Google)": f"https://www.google.com/search?q={vin_encoded}",
            "VIN (Yandex)": f"https://yandex.ru/search/?text={vin_encoded}",
        })

    return links


def format_car_report(plate: str | None = None, vin: str | None = None) -> str:
    """Формирует отчёт по автомобилю."""
    report = f"🚗 <b>Поиск по автомобилю</b>\n\n"

    if plate:
        report += f"🔢 <b>Госномер:</b> <code>{plate}</code>\n"
    if vin:
        report += f"🔑 <b>VIN:</b> <code>{vin}</code>\n"

    links = generate_car_search_links(plate, vin)

    report += f"\n🔎 <b>Сервисы для поиска:</b>\n"
    for category, cat_links in links.items():
        report += f"\n<b>{category}:</b>\n"
        for name, url in cat_links.items():
            report += f"• <a href=\"{url}\">{name}</a>\n"

    report += "\n\n💡 <i>Нажмите на ссылку для проверки авто</i>"

    return report

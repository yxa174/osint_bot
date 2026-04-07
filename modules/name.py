"""Модуль для поиска по ФИО — расширенный."""

import re
import logging
from urllib.parse import quote

log = logging.getLogger("OSINTBot")


def validate_name(text: str) -> dict | None:
    """Парсит ФИО из текста."""
    text = text.strip()

    # Фамилия Имя Отчество
    pattern = r"^([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)$"
    match = re.match(pattern, text)
    if match:
        return {
            "surname": match.group(1), "name": match.group(2),
            "patronymic": match.group(3), "full": text,
        }

    # Фамилия Имя
    pattern2 = r"^([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)$"
    match2 = re.match(pattern2, text)
    if match2:
        return {
            "surname": match2.group(1), "name": match2.group(2),
            "patronymic": None, "full": text,
        }

    return None


def generate_search_links(name_data: dict) -> dict:
    """Генерирует расширенные ссылки для поиска по ФИО."""
    surname = name_data["surname"]
    name = name_data["name"]
    patronymic = name_data.get("patronymic", "")
    full = name_data["full"]
    full_encoded = quote(full, safe="")
    sn_encoded = f"{surname} {name}"
    sn_encoded_url = quote(sn_encoded, safe="")

    links = {
        "Поисковики": {
            "Google": f"https://www.google.com/search?q={full_encoded}",
            "Yandex": f"https://yandex.ru/search/?text={full_encoded}",
            "Bing": f"https://www.bing.com/search?q={full_encoded}",
            "DuckDuckGo": f"https://duckduckgo.com/?q={full_encoded}",
            "Google (точное)": f"https://www.google.com/search?q=%22{full_encoded}%22",
        },
        "Соцсети РФ": {
            "VK": f"https://vk.com/people?q={sn_encoded_url}",
            "Одноклассники": f"https://ok.ru/search?st.cmd=sFriendSearch&st.query={sn_encoded_url}",
            "Мой Мир": f"https://my.mail.ru/search?query={sn_encoded_url}",
            "Facebook": f"https://www.facebook.com/search/people?q={sn_encoded_url}",
        },
        "Профессиональные": {
            "LinkedIn": f"https://www.linkedin.com/search/results/people/?keywords={sn_encoded_url}",
            "HH.ru": f"https://hh.ru/search/resume?text={full_encoded}&area=1",
            "SuperJob": f"https://www.superjob.ru/resume/search/?keywords={full_encoded}",
            "Avito Работа": f"https://www.avito.ru/rossiya?q={full_encoded}",
        },
        "Госреестры и суды": {
            "ФССП (долги)": f"https://fssp.gov.ru/iss/ip",
            "Картотека арбитражных дел": f"https://kad.arbitr.ru/",
            "Суды РФ (ГАС Правосудие)": f"https://ej.sudrf.ru/",
            "ФНС (ИП/ЮЛ)": f"https://www.nalog.ru/rn77/service/biz_find/",
            "Федресурс": f"https://fedresurs.ru/",
            "Роспатент": f"https://new.fips.ru/",
        },
        "Розыск и предупреждения": {
            "МВД Розыск": f"https://мвд.рф/wanted",
            "Интерпол": f"https://www.interpol.int/Notice/Search/Red",
        },
        "Прочее": {
            "Исполнители (ФНС)": f"https://service.nalog.ru/find.do",
            "Судебные приставы": f"https://fssp.gov.ru/iss/ip",
            "Доверенности": f"https://reestr-doverennostey.notariat.ru/",
            "Адвокаты": f"https://fpa RF.ru/reestr",
        },
    }

    return links


def format_name_report(name_data: dict) -> str:
    """Расширенный отчёт по ФИО."""
    surname = name_data["surname"]
    name = name_data["name"]
    patronymic = name_data.get("patronymic")

    report = f"👤 <b>Расширенный поиск по ФИО</b>\n\n"
    report += f"📝 <b>ФИО:</b> {surname} {name}"
    if patronymic:
        report += f" {patronymic}"
    report += "\n"
    report += f"🔤 <b>Инициалы:</b> {surname} {name[0]}.{patronymic[0] + '.' if patronymic else ''}\n"

    # Варианты написания
    variants = [
        f"{surname} {name}",
        f"{name} {surname}",
    ]
    if patronymic:
        variants.extend([
            f"{surname} {name} {patronymic}",
            f"{name} {patronymic} {surname}",
        ])
    report += f"\n🔀 <b>Варианты поиска:</b>\n"
    for v in variants:
        report += f"• {v}\n"

    # Латинская транслитерация
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    latin_surname = ''.join(translit_map.get(c.lower(), c) for c in surname)
    latin_name = ''.join(translit_map.get(c.lower(), c) for c in name)
    report += f"\n🔤 <b>Латиница:</b> {latin_surname} {latin_name}\n"

    # Ссылки
    search_links = generate_search_links(name_data)
    report += f"\n🔎 <b>Сервисы для поиска:</b>\n"
    for category, links in search_links.items():
        report += f"\n<b>{category}:</b>\n"
        for link_name, url in links.items():
            report += f"• <a href=\"{url}\">{link_name}</a>\n"

    report += "\n\n💡 <i>Нажмите на ссылку для ручного поиска информации</i>"

    return report

"""Модуль для поиска по ФИО."""

import re
import logging

log = logging.getLogger("OSINTBot")


def validate_name(text: str) -> dict | None:
    """Парсит ФИО из текста."""
    text = text.strip()

    # Паттерн: Фамилия Имя Отчество (символы, дефисы, пробелы)
    pattern = r"^([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)$"
    match = re.match(pattern, text)

    if match:
        return {
            "surname": match.group(1),
            "name": match.group(2),
            "patronymic": match.group(3),
            "full": text,
        }

    # Паттерн: Фамилия Имя
    pattern2 = r"^([А-ЯЁA-Z][а-яёa-z-]+)\s+([А-ЯЁA-Z][а-яёa-z-]+)$"
    match2 = re.match(pattern2, text)

    if match2:
        return {
            "surname": match2.group(1),
            "name": match2.group(2),
            "patronymic": None,
            "full": text,
        }

    return None


def generate_search_links(name_data: dict) -> list[dict]:
    """Генерирует ссылки для поиска по ФИО."""
    surname = name_data["surname"]
    name = name_data["name"]
    patronymic = name_data.get("patronymic", "")
    full = name_data["full"]

    links = [
        {
            "platform": "Google",
            "url": f"https://www.google.com/search?q={'+'.join(full.split())}",
            "icon": "🔍",
        },
        {
            "platform": "Yandex",
            "url": f"https://yandex.ru/search/?text={'+'.join(full.split())}",
            "icon": "🟡",
        },
        {
            "platform": "VK",
            "url": f"https://vk.com/people?q={surname} {name}",
            "icon": "🔵",
        },
        {
            "platform": "Одноклассники",
            "url": f"https://ok.ru/search?st.cmd=sFriendSearch&st.query={surname} {name}",
            "icon": "🟠",
        },
        {
            "platform": "Facebook",
            "url": f"https://www.facebook.com/search/people?q={surname}+{name}",
            "icon": "📘",
        },
        {
            "platform": "LinkedIn",
            "url": f"https://www.linkedin.com/search/results/people/?keywords={surname}+{name}",
            "icon": "💼",
        },
        {
            "platform": "TruePeopleSearch",
            "url": f"https://www.truepeoplesearch.com/results?name={full.replace(' ', '%20')}",
            "icon": "👤",
        },
        {
            "platform": "FamilyTree",
            "url": f"https://www.familysearch.org/search/name/results?name={surname}&givenname={name}",
            "icon": "🌳",
        },
    ]

    if patronymic:
        links.append({
            "platform": "ФНС (Физлица)",
            "url": f"https://www.nalog.ru/rn77/service/biz_find/?fl_fio={full.replace(' ', '%20')}",
            "icon": "🏛",
        })

    return links


def format_name_report(name_data: dict) -> str:
    """Формирует отчёт по поиску ФИО."""
    surname = name_data["surname"]
    name = name_data["name"]
    patronymic = name_data.get("patronymic")

    report = f"👤 <b>Поиск по ФИО</b>\n\n"
    report += f"📝 <b>ФИО:</b> {surname} {name}"
    if patronymic:
        report += f" {patronymic}"
    report += "\n\n"
    report += "🔗 <b>Ссылки для поиска:</b>\n\n"

    links = generate_search_links(name_data)
    for link in links:
        report += f"{link['icon']} <a href=\"{link['url']}\">{link['platform']}</a>\n"

    report += "\n💡 <i>Нажмите на ссылку для ручного поиска информации</i>"

    return report

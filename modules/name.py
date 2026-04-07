"""Модуль для поиска по ФИО — с реальными API."""

import re
import logging
import asyncio
from urllib.parse import quote

log = logging.getLogger("OSINTBot")


def validate_name(text: str) -> dict | None:
    """Парсит ФИО."""
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


async def search_ddg(query: str) -> dict:
    """DuckDuckGo Instant Answer API."""
    result = {"abstract": "", "abstract_url": "", "heading": "", "related": []}
    try:
        import httpx
        encoded = quote(query, safe="")
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1"
        headers = {"User-Agent": "OSINT-Bot/1.0"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                result["abstract"] = data.get("AbstractText", "")[:500]
                result["abstract_url"] = data.get("AbstractURL", "")
                result["heading"] = data.get("Heading", "")
                result["related"] = [
                    t.get("Text", "")
                    for t in data.get("RelatedTopics", [])[:5]
                    if t.get("Text")
                ]
    except Exception as e:
        log.debug(f"DDG error: {e}")
    return result


async def search_wikipedia(query: str, lang: str = "ru") -> list:
    """Wikipedia OpenSearch API."""
    results = []
    try:
        import httpx
        encoded = quote(query, safe="")
        url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={encoded}&limit=5&format=json"
        headers = {"User-Agent": "OSINT-Bot/1.0"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                titles = data[1] if len(data) > 1 else []
                descs = data[2] if len(data) > 2 else []
                urls = data[3] if len(data) > 3 else []
                results = list(zip(titles[:5], descs[:5], urls[:5]))
    except Exception as e:
        log.debug(f"Wikipedia ({lang}) error: {e}")
    return results


# Транслитерация
TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def transliterate(text: str) -> str:
    """Транслитерация кириллицы в латиницу."""
    return ''.join(TRANSLIT_MAP.get(c.lower(), c) for c in text)


async def search_name_everywhere(name_data: dict) -> str:
    """Полный поиск по ФИО с реальными данными."""
    surname = name_data["surname"]
    name = name_data["name"]
    patronymic = name_data.get("patronymic")

    # Транслитерация
    latin_surname = transliterate(surname)
    latin_name = transliterate(name)
    latin_patronymic = transliterate(patronymic) if patronymic else ""
    full_latin = f"{latin_surname} {latin_name}"
    if latin_patronymic:
        full_latin += f" {latin_patronymic}"

    # Параллельные запросы
    full_ru = name_data["full"]
    ddg_task = search_ddg(full_ru)
    wiki_ru_task = search_wikipedia(full_ru, "ru")
    wiki_en_task = search_wikipedia(full_latin, "en")

    ddg_data, wiki_ru, wiki_en = await asyncio.gather(ddg_task, wiki_ru_task, wiki_en_task, return_exceptions=True)
    if isinstance(ddg_data, Exception): ddg_data = {}
    if isinstance(wiki_ru, Exception): wiki_ru = []
    if isinstance(wiki_en, Exception): wiki_en = []

    # Формируем отчёт
    report = f"👤 <b>Расширенный поиск по ФИО</b>\n\n"
    report += f"📝 <b>ФИО:</b> {full_ru}\n"
    report += f"🔤 <b>Инициалы:</b> {surname} {name[0]}.{patronymic[0] + '.' if patronymic else ''}\n"

    # Транслитерация
    report += f"\n🔤 <b>Транслитерация:</b>\n"
    report += f"• Фамилия: <code>{latin_surname}</code>\n"
    report += f"• Имя: <code>{latin_name}</code>\n"
    if latin_patronymic:
        report += f"• Отчество: <code>{latin_patronymic}</code>\n"
    report += f"• Полное: <code>{full_latin}</code>\n"

    # DuckDuckGo
    if ddg_data.get("abstract"):
        report += f"\n📖 <b>DuckDuckGo:</b>\n"
        report += f"  {ddg_data['abstract']}\n"
        if ddg_data.get("abstract_url"):
            report += f"  🔗 <a href=\"{ddg_data['abstract_url']}\">Источник</a>\n"
        if ddg_data.get("related"):
            report += f"  Связанные запросы:\n"
            for rel in ddg_data["related"][:3]:
                report += f"    • {rel[:80]}\n"
    else:
        report += f"\n📖 <b>DuckDuckGo:</b> Нет мгновенных результатов\n"

    # Wikipedia RU
    if wiki_ru:
        report += f"\n📚 <b>Wikipedia (RU):</b>\n"
        for title, desc, url in wiki_ru[:5]:
            report += f"• <a href=\"{url}\">{title}</a>\n"
            if desc:
                report += f"  {desc[:100]}...\n"
    else:
        report += f"\n📚 <b>Wikipedia (RU):</b> Не найдено\n"

    # Wikipedia EN
    if wiki_en:
        report += f"\n🌍 <b>Wikipedia (EN):</b>\n"
        for title, desc, url in wiki_en[:3]:
            report += f"• <a href=\"{url}\">{title}</a>\n"

    # Реестры — информация
    report += f"\n🏛 <b>Госреестры (ручная проверка):</b>\n"
    report += f"• ФССП (долги): fssp.gov.ru/iss/ip\n"
    report += f"• Картотека дел: kad.arbitr.ru\n"
    report += f"• Суды РФ: ej.sudrf.ru\n"
    report += f"• ФНС (бизнес): nalog.ru\n"
    report += f"• Федресурс: fedresurs.ru\n"

    # Рекомендации
    report += f"\n💡 <b>Совет:</b> Используйте найденные ссылки Wikipedia и DuckDuckGo для дальнейшего поиска"

    return report

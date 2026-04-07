"""Модуль для поиска по username в соцсетях и платформах."""

import re
import logging
from typing import Any

log = logging.getLogger("OSINTBot")

# Список платформ для проверки username
PLATFORMS = [
    {"name": "Telegram", "url": "https://t.me/{username}", "check": True},
    {"name": "Instagram", "url": "https://instagram.com/{username}", "check": True},
    {"name": "TikTok", "url": "https://tiktok.com/@{username}", "check": True},
    {"name": "GitHub", "url": "https://github.com/{username}", "check": True},
    {"name": "Twitter/X", "url": "https://x.com/{username}", "check": True},
    {"name": "YouTube", "url": "https://youtube.com/@{username}", "check": True},
    {"name": "VK", "url": "https://vk.com/{username}", "check": True},
    {"name": "Facebook", "url": "https://facebook.com/{username}", "check": True},
    {"name": "LinkedIn", "url": "https://linkedin.com/in/{username}", "check": True},
    {"name": "Reddit", "url": "https://reddit.com/user/{username}", "check": True},
    {"name": "Pinterest", "url": "https://pinterest.com/{username}", "check": True},
    {"name": "Twitch", "url": "https://twitch.tv/{username}", "check": True},
    {"name": "Steam", "url": "https://steamcommunity.com/id/{username}", "check": True},
    {"name": "SoundCloud", "url": "https://soundcloud.com/{username}", "check": True},
    {"name": "Spotify", "url": "https://open.spotify.com/user/{username}", "check": True},
    {"name": "Docker Hub", "url": "https://hub.docker.com/u/{username}", "check": True},
    {"name": "Codeforces", "url": "https://codeforces.com/profile/{username}", "check": True},
    {"name": "LeetCode", "url": "https://leetcode.com/{username}", "check": True},
]


def validate_username(text: str) -> str | None:
    """Валидирует и очищает username."""
    text = text.strip().lstrip("@")
    # Username: 5-32 символа, буквы, цифры, подчёркивания
    if re.match(r"^[a-zA-Z0-9_]{5,32}$", text):
        return text
    return None


async def check_username_platform(username: str, platform: dict) -> dict[str, Any]:
    """Проверяет наличие username на конкретной платформе."""
    url = platform["url"].format(username=username)
    result = {
        "name": platform["name"],
        "url": url,
        "exists": None,  # None = неизвестно, True/False
        "status_code": None,
        "error": None,
    }

    if not platform.get("check"):
        return result

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})
            result["status_code"] = response.status_code

            # 200 = существует, 404 = нет, 403 = может существовать (ограниченный доступ)
            if response.status_code == 200:
                result["exists"] = True
            elif response.status_code == 404:
                result["exists"] = False
            elif response.status_code in (403, 301, 302):
                result["exists"] = None  # Неопределённо
            else:
                result["exists"] = response.status_code < 400

    except Exception as e:
        result["error"] = str(e)
        log.debug(f"Ошибка проверки {platform['name']}: {e}")

    return result


async def search_username(username: str) -> dict[str, Any]:
    """Полный поиск username по всем платформам."""
    results = []
    found = 0
    not_found = 0
    unknown = 0

    for platform in PLATFORMS:
        result = await check_username_platform(username, platform)
        results.append(result)

        if result["exists"] is True:
            found += 1
        elif result["exists"] is False:
            not_found += 1
        else:
            unknown += 1

    return {
        "username": username,
        "results": results,
        "found": found,
        "not_found": not_found,
        "unknown": unknown,
    }


def format_username_report(search_result: dict[str, Any]) -> str:
    """Формирует отчёт по поиску username."""
    username = search_result["username"]
    results = search_result["results"]

    report = f"👤 <b>Поиск по username: @{username}</b>\n\n"
    report += f"📊 <b>Итого:</b> найдено {search_result['found']} из {len(results)}\n\n"

    # Сначала показываем найденные
    found_platforms = [r for r in results if r["exists"] is True]
    if found_platforms:
        report += f"✅ <b>Найдено ({len(found_platforms)}):</b>\n"
        for r in found_platforms:
            report += f"• <a href=\"{r['url']}\">{r['name']}</a>\n"
        report += "\n"

    # Потом неизвестные
    unknown_platforms = [r for r in results if r["exists"] is None]
    if unknown_platforms:
        report += f"❓ <b>Не определено ({len(unknown_platforms)}):</b>\n"
        for r in unknown_platforms:
            report += f"• <a href=\"{r['url']}\">{r['name']}</a>\n"
        report += "\n"

    report += f"❌ <b>Не найдено ({search_result['not_found']}):</b>\n"
    not_found_platforms = [r for r in results if r["exists"] is False]
    for r in not_found_platforms[:5]:  # Показываем максимум 5
        report += f"• {r['name']}\n"
    if len(not_found_platforms) > 5:
        report += f"  ... и ещё {len(not_found_platforms) - 5}\n"

    return report

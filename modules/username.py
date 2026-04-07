"""Модуль для поиска по username — расширенный."""

import re
import logging
import asyncio
from typing import Any

log = logging.getLogger("OSINTBot")

PLATFORMS = [
    # Социальные сети
    {"name": "Telegram", "url": "https://t.me/{username}", "check": True},
    {"name": "Instagram", "url": "https://instagram.com/{username}", "check": True},
    {"name": "TikTok", "url": "https://tiktok.com/@{username}", "check": True},
    {"name": "Twitter/X", "url": "https://x.com/{username}", "check": True},
    {"name": "Facebook", "url": "https://facebook.com/{username}", "check": True},
    {"name": "VK", "url": "https://vk.com/{username}", "check": True},
    {"name": "Одноклассники", "url": "https://ok.ru/profile/{username}", "check": True},
    # Разработка и IT
    {"name": "GitHub", "url": "https://github.com/{username}", "check": True},
    {"name": "GitLab", "url": "https://gitlab.com/{username}", "check": True},
    {"name": "Bitbucket", "url": "https://bitbucket.org/{username}/", "check": True},
    {"name": "StackOverflow", "url": "https://stackoverflow.com/users/search?q={username}", "check": False},
    {"name": "Codeforces", "url": "https://codeforces.com/profile/{username}", "check": True},
    {"name": "LeetCode", "url": "https://leetcode.com/{username}", "check": True},
    {"name": "Docker Hub", "url": "https://hub.docker.com/u/{username}", "check": True},
    {"name": "npm", "url": "https://www.npmjs.com/~{username}", "check": True},
    {"name": "PyPI", "url": "https://pypi.org/user/{username}/", "check": True},
    {"name": "HackerRank", "url": "https://hackerrank.com/{username}", "check": True},
    # Видео и стриминг
    {"name": "YouTube", "url": "https://youtube.com/@{username}", "check": True},
    {"name": "Twitch", "url": "https://twitch.tv/{username}", "check": True},
    {"name": "Rutube", "url": "https://rutube.ru/people/{username}", "check": True},
    {"name": "Dailymotion", "url": "https://dailymotion.com/{username}", "check": True},
    # Музыка
    {"name": "SoundCloud", "url": "https://soundcloud.com/{username}", "check": True},
    {"name": "Spotify", "url": "https://open.spotify.com/user/{username}", "check": True},
    {"name": "Last.fm", "url": "https://last.fm/user/{username}", "check": True},
    {"name": "Bandcamp", "url": "https://bandcamp.com/{username}", "check": True},
    # Игры
    {"name": "Steam", "url": "https://steamcommunity.com/id/{username}", "check": True},
    {"name": "Xbox", "url": "https://xboxgamertag.com/search/{username}", "check": False},
    {"name": "PSN", "url": "https://psnprofiles.com/xhr/search/users?q={username}", "check": False},
    {"name": "Epic Games", "url": "https://fortnitetracker.com/nitro?epicName={username}", "check": False},
    {"name": "Chess.com", "url": "https://chess.com/member/{username}", "check": True},
    {"name": "Lichess", "url": "https://lichess.org/@/{username}", "check": True},
    # Фото и дизайн
    {"name": "Pinterest", "url": "https://pinterest.com/{username}", "check": True},
    {"name": "Flickr", "url": "https://flickr.com/people/{username}", "check": True},
    {"name": "Behance", "url": "https://behance.net/{username}", "check": True},
    {"name": "Dribbble", "url": "https://dribbble.com/{username}", "check": True},
    {"name": "DeviantArt", "url": "https://deviantart.com/{username}", "check": True},
    {"name": "Unsplash", "url": "https://unsplash.com/@{username}", "check": True},
    # Блоги и форумы
    {"name": "Reddit", "url": "https://reddit.com/user/{username}", "check": True},
    {"name": "Medium", "url": "https://medium.com/@{username}", "check": True},
    {"name": "Tumblr", "url": "https://{username}.tumblr.com", "check": True},
    {"name": "WordPress", "url": "https://{username}.wordpress.com", "check": True},
    {"name": "Blogger", "url": "https://{username}.blogspot.com", "check": True},
    {"name": "LiveJournal", "url": "https://{username}.livejournal.com", "check": True},
    {"name": "Habr", "url": "https://habr.com/ru/users/{username}", "check": True},
    {"name": "Pikabu", "url": "https://pikabu.ru/@{username}", "check": True},
    {"name": "VC.ru", "url": "https://vc.ru/u/{username}", "check": True},
    # Бизнес и финансы
    {"name": "Patreon", "url": "https://patreon.com/{username}", "check": True},
    {"name": "PayPal (.me)", "url": "https://paypal.me/{username}", "check": True},
    {"name": "LinkedIn", "url": "https://linkedin.com/in/{username}", "check": True},
    {"name": "About.me", "url": "https://about.me/{username}", "check": True},
    {"name": "Gravatar", "url": "https://en.gravatar.com/{username}", "check": True},
    # Прочее
    {"name": "Wikipedia", "url": "https://en.wikipedia.org/wiki/User:{username}", "check": True},
    {"name": "Telegram (старая)", "url": "https://telegram.me/{username}", "check": True},
    {"name": "Trello", "url": "https://trello.com/{username}", "check": True},
    {"name": "Mastodon", "url": "https://mastodon.social/@{username}", "check": True},
    {"name": "Threads", "url": "https://threads.net/@{username}", "check": True},
    {"name": "Discord (lookup)", "url": "https://discord.id/", "check": False},
    {"name": "Keybase", "url": "https://keybase.io/{username}", "check": True},
    {"name": "Internet Archive", "url": "https://archive.org/search?query={username}", "check": False},
]


def validate_username(text: str) -> str | None:
    """Валидирует и очищает username."""
    text = text.strip().lstrip("@")
    if re.match(r"^[a-zA-Z0-9_]{3,50}$", text):
        return text
    return None


async def check_platform(username: str, platform: dict) -> dict[str, Any]:
    """Проверяет наличие username на платформе."""
    url = platform["url"].format(username=username)
    result = {
        "name": platform["name"], "url": url,
        "exists": None, "status_code": None, "error": None,
    }

    if not platform.get("check"):
        return result

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            response = await client.get(url, headers=headers)
            result["status_code"] = response.status_code

            if response.status_code == 200:
                result["exists"] = True
            elif response.status_code == 404:
                result["exists"] = False
            elif response.status_code in (403, 301, 302):
                result["exists"] = None
            else:
                result["exists"] = response.status_code < 400

    except Exception as e:
        result["error"] = str(e)
        log.debug(f"Ошибка проверки {platform['name']}: {e}")

    return result


async def search_username(username: str) -> dict[str, Any]:
    """Полный поиск username по платформам."""
    results = []
    found = 0
    not_found = 0
    unknown = 0

    # Проверяем платформами пачками по 10
    batch_size = 10
    for i in range(0, len(PLATFORMS), batch_size):
        batch = PLATFORMS[i:i + batch_size]
        tasks = [check_platform(username, p) for p in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in batch_results:
            if isinstance(r, Exception):
                continue
            results.append(r)
            if r["exists"] is True:
                found += 1
            elif r["exists"] is False:
                not_found += 1
            else:
                unknown += 1

    return {
        "username": username, "results": results,
        "found": found, "not_found": not_found, "unknown": unknown,
    }


def format_username_report(search_result: dict[str, Any]) -> str:
    """Расширенный отчёт по username."""
    username = search_result["username"]
    results = search_result["results"]
    total = len(results)

    report = f"👤 <b>Расширенный поиск: @{username}</b>\n\n"
    report += f"📊 <b>Итого:</b> найдено {search_result['found']} из {total} платформ\n"
    report += f"❓ <b>Не определено:</b> {search_result['unknown']}\n"
    report += f"❌ <b>Не найдено:</b> {search_result['not_found']}\n\n"

    # Найденные
    found_platforms = [r for r in results if r["exists"] is True]
    if found_platforms:
        report += f"✅ <b>Найдено ({len(found_platforms)}):</b>\n"
        for r in found_platforms:
            report += f"• <a href=\"{r['url']}\">{r['name']}</a>\n"
        report += "\n"

    # Неизвестные
    unknown_platforms = [r for r in results if r["exists"] is None]
    if unknown_platforms:
        report += f"❓ <b>Не определено ({len(unknown_platforms)}):</b>\n"
        for r in unknown_platforms:
            report += f"• <a href=\"{r['url']}\">{r['name']}</a>\n"
        report += "\n"

    # Не найденные
    not_found_platforms = [r for r in results if r["exists"] is False]
    if not_found_platforms:
        report += f"❌ <b>Не найдено ({len(not_found_platforms)}):</b>\n"
        for r in not_found_platforms:
            report += f"• {r['name']}\n"

    # Ссылки для ручного поиска
    from urllib.parse import quote
    encoded = quote(username, safe="")
    report += f"\n🔎 <b>Дополнительный поиск:</b>\n"
    report += f"• <a href=\"https://www.google.com/search?q=%22{username}%22\">Google</a>\n"
    report += f"• <a href=\"https://yandex.ru/search/?text=%22{username}%22\">Yandex</a>\n"
    report += f"• <a href=\"https://namechk.com/\">Namechk</a>\n"
    report += f"• <a href=\"https://whatsmyname.app/?q={encoded}\">WhatsMyName</a>\n"
    report += f"• <a href=\"https://maigret.app/\">Maigret</a>\n"

    report += "\n💡 <i>Нажмите на ссылку для перехода на профиль</i>"

    return report

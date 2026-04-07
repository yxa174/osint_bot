"""Модуль для поиска по email — расширенный."""

import re
import logging
import asyncio

log = logging.getLogger("OSINTBot")


def validate_email(text: str) -> str | None:
    """Валидирует email адрес."""
    text = text.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, text):
        return text
    return None


def parse_email(email: str) -> dict:
    """Расширенный парсинг email."""
    local_part, domain = email.rsplit("@", 1)

    result = {
        "email": email,
        "local_part": local_part,
        "domain": domain,
        "provider": detect_provider(domain),
        "is_disposable": is_disposable_domain(domain),
        "is_free": is_free_provider(domain),
        "is_role_account": is_role_account(local_part),
        "gravatar": f"https://www.gravatar.com/avatar/{hash_email(email)}?d=404&s=200",
        "google_account": domain in ("gmail.com", "googlemail.com"),
        "microsoft_account": domain in ("hotmail.com", "outlook.com", "live.com", "msn.com"),
        "yandex_account": domain in ("yandex.ru", "ya.ru", "yandex.com", "yandex.by", "yandex.kz"),
        "mail_ru_account": domain in ("mail.ru", "list.ru", "bk.ru", "inbox.ru"),
    }

    return result


def detect_provider(domain: str) -> str:
    providers = {
        "gmail.com": "Google (Gmail)", "googlemail.com": "Google (Gmail)",
        "yahoo.com": "Yahoo Mail", "yahoo.ru": "Yahoo Mail",
        "hotmail.com": "Microsoft (Hotmail)", "outlook.com": "Microsoft (Outlook)",
        "live.com": "Microsoft (Live)", "msn.com": "Microsoft (MSN)",
        "mail.ru": "Mail.ru", "yandex.ru": "Yandex Mail",
        "ya.ru": "Yandex Mail", "rambler.ru": "Rambler",
        "list.ru": "Mail.ru (List)", "bk.ru": "Mail.ru (BK)",
        "inbox.ru": "Mail.ru (Inbox)",
        "icloud.com": "Apple (iCloud)", "me.com": "Apple (Me)",
        "mac.com": "Apple (Mac)",
        "protonmail.com": "ProtonMail", "proton.me": "ProtonMail",
        "tutanota.com": "Tutanota", "tuta.io": "Tutanota",
        "zoho.com": "Zoho Mail", "aol.com": "AOL Mail",
        "gmx.com": "GMX", "fastmail.com": "Fastmail",
        "duck.com": "DuckDuckGo Email", "simplelogin.com": "SimpleLogin",
        "anonaddy.com": "AnonAddy",
    }
    return providers.get(domain.lower(), f"Кастомный домен ({domain})")


def is_disposable_domain(domain: str) -> bool:
    disposable = {
        "tempmail.com", "throwaway.email", "guerrillamail.com",
        "mailinator.com", "yopmail.com", "sharklasers.com",
        "guerrillamailblock.com", "grr.la", "dispostable.com",
        "tempail.com", "fakeinbox.com", "trashmail.com",
        "10minutemail.com", "temp-mail.org", "burnermail.io",
        "maildrop.cc", "getairmail.com", "mailnesia.com",
    }
    return domain.lower() in disposable


def is_free_provider(domain: str) -> bool:
    free = {
        "gmail.com", "yahoo.com", "yahoo.ru", "hotmail.com", "outlook.com",
        "mail.ru", "yandex.ru", "ya.ru", "rambler.ru", "list.ru", "bk.ru",
        "inbox.ru", "icloud.com", "protonmail.com", "live.com", "msn.com",
    }
    return domain.lower() in free


def is_role_account(local_part: str) -> bool:
    roles = {
        "admin", "info", "support", "sales", "contact", "help",
        "noreply", "no-reply", "webmaster", "postmaster", "hostmaster",
        "abuse", "security", "billing", "office", "team", "hr",
        "marketing", "press", "media", "legal", "compliance",
    }
    return local_part.lower().rstrip(".") in roles


def hash_email(email: str) -> str:
    import hashlib
    return hashlib.md5(email.lower().strip().encode()).hexdigest()


def get_email_search_links(email: str) -> dict:
    """Генерирует ссылки для поиска по email."""
    from urllib.parse import quote
    encoded = quote(email, safe="")

    return {
        "Поисковики": {
            "Google": f"https://www.google.com/search?q={encoded}",
            "Yandex": f"https://yandex.ru/search/?text={encoded}",
            "DuckDuckGo": f"https://duckduckgo.com/?q={encoded}",
        },
        "Утечки": {
            "Have I Been Pwned": f"https://haveibeenpwned.com/account/{email}",
            "DeHashed": f"https://dehashed.com/search?query={encoded}",
            "LeakCheck": f"https://leakcheck.io/check/{encoded}",
            "SnusBase": "https://snusbase.com/",
            "Intelligence X": f"https://intelx.io/?s={encoded}",
        },
        "Профили": {
            "Gravatar": f"https://www.gravatar.com/avatar/{hash_email(email)}?d=identicon&s=200",
            "GitHub": f"https://github.com/search?q={encoded}&type=users",
            "GitLab": f"https://gitlab.com/search?search={encoded}&nav_source=navbar",
            "Google Account": f"https://accounts.google.com/accountrestore",
        },
        "Верификация": {
            "EmailHippo": "https://tools.emailhippo.com/email/",
            "MailTester": f"https://mailtester.com/testmail.php?lang=en&email={encoded}",
            "VerifyEmail": f"https://verify-email.org/?email={encoded}",
        },
    }


async def check_email_breaches(email: str, api_key: str | None = None) -> dict:
    """Проверка в утечках через Have I Been Pwned API."""
    result = {"breaches": [], "pastes": [], "error": None}

    if not api_key:
        result["error"] = "HIBP API ключ не указан"
        return result

    try:
        import httpx
        headers = {"hibp-api-version": "3", "user-agent": "OSINT-Bot/1.0"}

        async with httpx.AsyncClient(timeout=15) as client:
            # Утечки
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                breaches = resp.json()
                result["breaches"] = [
                    {
                        "name": b.get("Name", "Unknown"),
                        "date": b.get("BreachDate", "Unknown"),
                        "added": b.get("AddedDate", "Unknown"),
                        "pwn_count": b.get("PwnCount", 0),
                        "data_classes": b.get("DataClasses", []),
                        "description": b.get("Description", ""),
                    }
                    for b in breaches[:10]
                ]

            # Пасты
            url_paste = f"https://haveibeenpwned.com/api/v3/pasteaccount/{email}"
            resp_paste = await client.get(url_paste, headers=headers)
            if resp_paste.status_code == 200:
                pastes = resp_paste.json()
                result["pastes"] = [
                    {
                        "source": p.get("Source", "Unknown"),
                        "date": p.get("Date", "Unknown"),
                        "email_count": p.get("EmailCount", 0),
                    }
                    for p in pastes[:5]
                ]

            elif resp.status_code == 404:
                pass  # Не найден — хорошо
            elif resp.status_code == 403:
                result["error"] = "API ключ недействителен"
            else:
                result["error"] = f"Ошибка API: {resp.status_code}"

    except Exception as e:
        log.error(f"Ошибка проверки email в утечках: {e}")
        result["error"] = str(e)

    return result


def format_email_report(email: str, breach_data: dict | None = None) -> str:
    """Расширенный отчёт по email."""
    data = parse_email(email)
    search_links = get_email_search_links(email)

    report = f"📧 <b>Расширенный поиск по email</b>\n\n"
    report += f"📮 <b>Email:</b> <code>{data['email']}</code>\n"
    report += f"👤 <b>Локальная часть:</b> <code>{data['local_part']}</code>\n"
    report += f"🌐 <b>Домен:</b> <code>{data['domain']}</code>\n"
    report += f"🏢 <b>Провайдер:</b> {data['provider']}\n"
    report += f"🆓 <b>Бесплатный:</b> {'Да' if data['is_free'] else 'Нет (корпоративный)'}\n"
    report += f"⚠️ <b>Временный:</b> {'Да' if data['is_disposable'] else 'Нет'}\n"
    report += f"👔 <b>Ролевой:</b> {'Да' if data['is_role_account'] else 'Нет'}\n"
    report += f"🖼 <b>Gravatar:</b> <a href=\"{data['gravatar']}\">Проверить</a>\n"

    # Привязка к экосистемам
    ecosystems = []
    if data["google_account"]: ecosystems.append("Google")
    if data["microsoft_account"]: ecosystems.append("Microsoft")
    if data["yandex_account"]: ecosystems.append("Яндекс")
    if data["mail_ru_account"]: ecosystems.append("Mail.ru")
    if ecosystems:
        report += f"\n🔗 <b>Экосистемы:</b> {', '.join(ecosystems)}\n"

    # Утечки
    if breach_data:
        breaches = breach_data.get("breaches", [])
        pastes = breach_data.get("pastes", [])

        if breaches:
            total_pwned = sum(b.get("pwn_count", 0) for b in breaches)
            report += f"\n🚨 <b>Найдено в {len(breaches)} утечках ({total_pwned:,} записей):</b>\n"
            for b in breaches:
                classes = ", ".join(b.get("data_classes", [])[:5])
                report += f"\n• <b>{b['name']}</b> ({b['date']})\n"
                report += f"  Записей: {b['pwn_count']:,}\n"
                report += f"  Данные: {classes}\n"
        else:
            report += f"\n✅ <b>Не найден в известных утечках</b>\n"

        if pastes:
            report += f"\n📋 <b>Найдено в {len(pastes)} пастах:</b>\n"
            for p in pastes:
                report += f"• {p['source']} ({p['date']}) — {p['email_count']:,} email\n"

        if breach_data.get("error"):
            report += f"\n⚠️ <b>HIBP:</b> {breach_data['error']}\n"

    # Ссылки
    report += f"\n🔎 <b>Сервисы для поиска:</b>\n"
    for category, links in search_links.items():
        report += f"\n<b>{category}:</b>\n"
        for name, url in links.items():
            report += f"• <a href=\"{url}\">{name}</a>\n"

    report += "\n💡 <i>Нажмите на ссылку для поиска дополнительной информации</i>"

    return report

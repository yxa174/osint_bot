"""Модуль для поиска по email — с реальными API-запросами."""

import re
import logging
import hashlib
import json

log = logging.getLogger("OSINTBot")


def validate_email(text: str) -> str | None:
    """Валидирует email."""
    text = text.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, text):
        return text
    return None


def parse_email_local(email: str) -> dict:
    """Локальный парсинг email."""
    local_part, domain = email.rsplit("@", 1)

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

    disposable = {
        "tempmail.com", "throwaway.email", "guerrillamail.com",
        "mailinator.com", "yopmail.com", "sharklasers.com",
        "guerrillamailblock.com", "grr.la", "dispostable.com",
        "tempail.com", "fakeinbox.com", "trashmail.com",
        "10minutemail.com", "temp-mail.org", "burnermail.io",
        "maildrop.cc", "getairmail.com", "mailnesia.com",
    }

    free_providers = {
        "gmail.com", "yahoo.com", "yahoo.ru", "hotmail.com", "outlook.com",
        "mail.ru", "yandex.ru", "ya.ru", "rambler.ru", "list.ru", "bk.ru",
        "inbox.ru", "icloud.com", "protonmail.com", "live.com", "msn.com",
    }

    role_accounts = {
        "admin", "info", "support", "sales", "contact", "help",
        "noreply", "no-reply", "webmaster", "postmaster", "hostmaster",
        "abuse", "security", "billing", "office", "team", "hr",
        "marketing", "press", "media", "legal", "compliance",
    }

    md5_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()

    return {
        "email": email,
        "local_part": local_part,
        "domain": domain,
        "provider": providers.get(domain.lower(), f"Кастомный домен ({domain})"),
        "is_disposable": domain.lower() in disposable,
        "is_free": domain.lower() in free_providers,
        "is_role_account": local_part.lower().rstrip(".") in role_accounts,
        "gravatar_url": f"https://www.gravatar.com/avatar/{md5_hash}?d=identicon&s=200",
        "md5_hash": md5_hash,
        "google_account": domain.lower() in ("gmail.com", "googlemail.com"),
        "microsoft_account": domain.lower() in ("hotmail.com", "outlook.com", "live.com", "msn.com"),
        "yandex_account": domain.lower() in ("yandex.ru", "ya.ru", "yandex.com", "yandex.by", "yandex.kz"),
        "mail_ru_account": domain.lower() in ("mail.ru", "list.ru", "bk.ru", "inbox.ru"),
    }


async def check_hibp(email: str, api_key: str) -> dict:
    """Have I Been Pwned — проверка утечек."""
    result = {"breaches": [], "pastes": [], "error": None}
    if not api_key:
        result["error"] = "API ключ не указан"
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
                    for b in breaches[:15]
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
        log.error(f"Ошибка HIBP: {e}")
        result["error"] = str(e)

    return result


async def check_emailrep(email: str) -> dict:
    """EmailRep.io — репутация email (бесплатно, без ключа)."""
    result = {}
    try:
        import httpx
        url = f"https://emailrep.io/{email}"
        headers = {"Accept": "application/json", "User-Agent": "OSINT-Bot/1.0"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "reputation": data.get("reputation", "Unknown"),
                    "suspicious": data.get("suspicious", False),
                    "references": data.get("references", 0),
                    "details": {
                        "blacklisted": data.get("details", {}).get("blacklisted", False),
                        "malicious_activity": data.get("details", {}).get("malicious_activity", False),
                        "recent_abuse": data.get("details", {}).get("recent_abuse", False),
                        "fraud": data.get("details", {}).get("fraud", False),
                        "spam": data.get("details", {}).get("spam", False),
                        "spam_filter": data.get("details", {}).get("spam_filter", False),
                        "disposable": data.get("details", {}).get("disposable", False),
                        "has_mx_records": data.get("details", {}).get("has_mx_records", False),
                        "domain_created": data.get("details", {}).get("domain_created", "Unknown"),
                        "domain_age_days": data.get("details", {}).get("domain_age_days", "Unknown"),
                        "free_provider": data.get("details", {}).get("free_provider", False),
                    },
                }
    except Exception as e:
        log.debug(f"EmailRep error: {e}")

    return result


async def check_hunter_domain(domain: str, api_key: str) -> dict:
    """Hunter.io — информация о домене."""
    result = {}
    if not api_key:
        return result

    try:
        import httpx
        url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                result = {
                    "domain": data.get("domain", ""),
                    "org_name": data.get("organization", ""),
                    "emails_found": data.get("total", 0),
                    "emails": data.get("emails", [])[:10],
                    "pattern": data.get("pattern", ""),
                    "webmail": data.get("webmail", False),
                    "disposable": data.get("disposable", False),
                    "accept_all": data.get("accept_all", False),
                }
    except Exception as e:
        log.debug(f"Hunter.io error: {e}")

    return result


async def check_gravatar(email: str) -> dict:
    """Проверка наличия профиля Gravatar."""
    result = {"exists": False, "username": "", "display_name": "", "urls": []}
    try:
        import httpx
        md5_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
        url = f"https://en.gravatar.com/{md5_hash}.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                entry = data.get("entry", [{}])[0]
                result["exists"] = True
                result["username"] = entry.get("preferredUsername", "")
                result["display_name"] = entry.get("displayName", "")
                result["urls"] = [
                    {"title": u.get("title", ""), "url": u.get("value", "")}
                    for u in entry.get("accounts", [])
                ]
    except Exception:
        pass

    return result


async def search_email_everywhere(email: str) -> str:
    """Полный поиск по email с реальными данными."""
    validated = validate_email(email)
    if not validated:
        return "❌ Неверный формат email.\n\nПример: <code>user@gmail.com</code>"

    import config

    # Параллельные запросы
    local_data = parse_email_local(validated)
    hibp_task = check_hibp(validated, config.HIBP_API_KEY) if config.HIBP_API_KEY else None
    emailrep_task = check_emailrep(validated)
    gravatar_task = check_gravatar(validated)

    # Hunter для кастомных доменов
    hunter_task = None
    if config.HUNTER_API_KEY and not local_data["is_free"]:
        hunter_task = check_hunter_domain(local_data["domain"], config.HUNTER_API_KEY)

    # Ждём все запросы
    tasks = [emailrep_task, gravatar_task]
    if hibp_task:
        tasks.append(hibp_task)
    if hunter_task:
        tasks.append(hunter_task)

    results = await __import__("asyncio").gather(*tasks, return_exceptions=True)

    emailrep_data = results[0] if not isinstance(results[0], Exception) else {}
    gravatar_data = results[1] if not isinstance(results[1], Exception) else {}
    hibp_data = results[2] if not isinstance(results[2], Exception) else {} if hibp_task else {}
    hunter_data = results[3] if not isinstance(results[3], Exception) else {} if hunter_task else {}

    # Формируем отчёт
    report = f"📧 <b>Расширенный поиск по email</b>\n\n"
    report += f"📮 <b>Email:</b> <code>{validated}</code>\n"
    report += f"👤 <b>Локальная часть:</b> <code>{local_data['local_part']}</code>\n"
    report += f"🌐 <b>Домен:</b> <code>{local_data['domain']}</code>\n"
    report += f"🏢 <b>Провайдер:</b> {local_data['provider']}\n"
    report += f"🆓 <b>Бесплатный:</b> {'Да' if local_data['is_free'] else 'Нет (корпоративный)'}\n"
    report += f"⚠️ <b>Временный:</b> {'Да' if local_data['is_disposable'] else 'Нет'}\n"
    report += f"👔 <b>Ролевой:</b> {'Да' if local_data['is_role_account'] else 'Нет'}\n"

    # Экосистемы
    ecosystems = []
    if local_data["google_account"]: ecosystems.append("Google")
    if local_data["microsoft_account"]: ecosystems.append("Microsoft")
    if local_data["yandex_account"]: ecosystems.append("Яндекс")
    if local_data["mail_ru_account"]: ecosystems.append("Mail.ru")
    if ecosystems:
        report += f"\n🔗 <b>Экосистемы:</b> {', '.join(ecosystems)}\n"

    # Gravatar
    if gravatar_data.get("exists"):
        report += f"\n🖼 <b>Gravatar:</b>\n"
        report += f"  👤 Имя: {gravatar_data['display_name']}\n"
        report += f"  🔗 Username: @{gravatar_data['username']}\n"
        if gravatar_data.get("urls"):
            report += f"  📎 Привязанные аккаунты:\n"
            for acc in gravatar_data["urls"][:5]:
                if acc.get("title") and acc.get("url"):
                    report += f"    • <a href=\"{acc['url']}\">{acc['title']}</a>\n"
    else:
        report += f"\n🖼 <b>Gravatar:</b> Не найден\n"

    # EmailRep — репутация
    if emailrep_data:
        rep = emailrep_data.get("reputation", "Unknown")
        rep_emoji = {"none": "⚪", "low": "🟡", "medium": "🟠", "high": "🟢"}.get(rep.lower(), "⚪")
        report += f"\n{rep_emoji} <b>Репутация (EmailRep):</b> {rep}\n"
        report += f"  📊 Ссылок в сети: {emailrep_data.get('references', 0)}\n"
        report += f"  ⚠️ Подозрительный: {'Да' if emailrep_data.get('suspicious') else 'Нет'}\n"

        details = emailrep_data.get("details", {})
        if details.get("blacklisted"):
            report += f"  🚫 В чёрных списках: Да\n"
        if details.get("malicious_activity"):
            report += f"  🔴 Замечен в вредоносной активности\n"
        if details.get("recent_abuse"):
            report += f"  🚨 Недавние случаи злоупотребления\n"
        if details.get("fraud"):
            report += f"  💣 Связан с мошенничеством\n"
        if details.get("spam"):
            report += f"  📬 Отмечен как спам\n"
        if details.get("domain_age_days") and details["domain_age_days"] != "Unknown":
            report += f"  📅 Возраст домена: {details['domain_age_days']} дней\n"
        if details.get("domain_created") and details["domain_created"] != "Unknown":
            report += f"  📅 Домен создан: {details['domain_created']}\n"

    # Hunter — данные о домене
    if hunter_data:
        report += f"\n🏢 <b>Домен (Hunter.io):</b>\n"
        if hunter_data.get("org_name"):
            report += f"  Организация: {hunter_data['org_name']}\n"
        report += f"  Найдено email: {hunter_data.get('emails_found', 0)}\n"
        if hunter_data.get("pattern"):
            report += f"  Паттерн: {hunter_data['pattern']}\n"
        if hunter_data.get("emails"):
            report += f"  📧 Найденные адреса:\n"
            for e in hunter_data["emails"][:5]:
                report += f"    • {e.get('value', '')} ({e.get('position', '')})\n"

    # HIBP — утечки
    if hibp_data:
        breaches = hibp_data.get("breaches", [])
        pastes = hibp_data.get("pastes", [])

        if breaches:
            total_pwned = sum(b.get("pwn_count", 0) for b in breaches)
            report += f"\n🚨 <b>Найдено в {len(breaches)} утечках ({total_pwned:,} записей):</b>\n"
            for b in breaches:
                classes = ", ".join(b.get("data_classes", [])[:5])
                report += f"\n• <b>{b['name']}</b> ({b['date']})\n"
                report += f"  Записей: {b['pwn_count']:,}\n"
                if b.get("description"):
                    desc = b["description"][:100]
                    report += f"  {desc}...\n"
                report += f"  Данные: {classes}\n"
        else:
            report += f"\n✅ <b>Не найден в известных утечках</b>\n"

        if pastes:
            report += f"\n📋 <b>Найдено в {len(pastes)} пастах:</b>\n"
            for p in pastes:
                report += f"• {p['source']} ({p['date']}) — {p['email_count']:,} email\n"

        if hibp_data.get("error"):
            report += f"\n⚠️ <b>HIBP:</b> {hibp_data['error']}\n"

    report += "\n\n💡 <i>Данные собраны из открытых источников и API</i>"

    return report

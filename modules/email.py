"""Модуль для поиска информации по email."""

import re
import logging

log = logging.getLogger("OSINTBot")


def validate_email(text: str) -> str | None:
    """Валидирует email адрес."""
    text = text.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, text):
        return text
    return None


def parse_email(email: str) -> dict:
    """Парсит email и извлекает информацию."""
    local_part, domain = email.rsplit("@", 1)

    result = {
        "email": email,
        "valid": True,
        "local_part": local_part,
        "domain": domain,
        "provider": detect_provider(domain),
        "is_disposable": is_disposable_domain(domain),
        "gravatar": f"https://www.gravatar.com/avatar/{hash_email(email)}?d=404&s=200",
    }

    return result


def detect_provider(domain: str) -> str:
    """Определяет провайдера email."""
    providers = {
        "gmail.com": "Google (Gmail)",
        "yahoo.com": "Yahoo Mail",
        "yahoo.ru": "Yahoo Mail",
        "hotmail.com": "Microsoft (Hotmail)",
        "outlook.com": "Microsoft (Outlook)",
        "mail.ru": "Mail.ru",
        "yandex.ru": "Yandex Mail",
        "ya.ru": "Yandex Mail",
        "rambler.ru": "Rambler",
        "list.ru": "Mail.ru (List)",
        "bk.ru": "Mail.ru (BK)",
        "inbox.ru": "Mail.ru (Inbox)",
        "icloud.com": "Apple (iCloud)",
        "me.com": "Apple (Me)",
        "mac.com": "Apple (Mac)",
        "protonmail.com": "ProtonMail",
        "proton.me": "ProtonMail",
        "tutanota.com": "Tutanota",
        "tuta.io": "Tutanota",
        "zoho.com": "Zoho Mail",
        "aol.com": "AOL Mail",
        "gmx.com": "GMX",
        "fastmail.com": "Fastmail",
    }
    return providers.get(domain.lower(), f"Кастомный домен ({domain})")


def is_disposable_domain(domain: str) -> bool:
    """Проверяет, является ли домен временным."""
    disposable = {
        "tempmail.com", "throwaway.email", "guerrillamail.com",
        "mailinator.com", "yopmail.com", "sharklasers.com",
        "guerrillamailblock.com", "grr.la", "dispostable.com",
        "tempail.com", "fakeinbox.com", "trashmail.com",
    }
    return domain.lower() in disposable


def hash_email(email: str) -> str:
    """Хеширует email для Gravatar."""
    import hashlib
    return hashlib.md5(email.lower().strip().encode()).hexdigest()


async def check_email_breaches(email: str, api_key: str | None = None) -> dict:
    """Проверяет email в утечках через Have I Been Pwned API."""
    result = {
        "breaches": [],
        "paste_count": 0,
        "error": None,
    }

    if not api_key:
        result["error"] = "HIBP API ключ не указан"
        return result

    try:
        import httpx
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        headers = {
            "hibp-api-version": "3",
            "user-agent": "OSINT-Bot/1.0",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                breaches = response.json()
                result["breaches"] = [
                    {
                        "name": b.get("Name", "Unknown"),
                        "date": b.get("BreachDate", "Unknown"),
                        "data_classes": b.get("DataClasses", []),
                    }
                    for b in breaches[:10]  # Ограничиваем 10
                ]
            elif response.status_code == 404:
                pass  # Не найден в утечках — хорошо
            elif response.status_code == 403:
                result["error"] = "API ключ недействителен"
            else:
                result["error"] = f"Ошибка API: {response.status_code}"

    except Exception as e:
        log.error(f"Ошибка проверки email в утечках: {e}")
        result["error"] = str(e)

    return result


def format_email_report(email: str, breach_data: dict | None = None) -> str:
    """Формирует отчёт по email."""
    data = parse_email(email)

    report = f"📧 <b>Поиск по email</b>\n\n"
    report += f"📮 <b>Email:</b> <code>{data['email']}</code>\n"
    report += f"👤 <b>Локальная часть:</b> <code>{data['local_part']}</code>\n"
    report += f"🌐 <b>Домен:</b> <code>{data['domain']}</code>\n"
    report += f"🏢 <b>Провайдер:</b> {data['provider']}\n"
    report += f"⚠️ <b>Временный email:</b> {'Да' if data['is_disposable'] else 'Нет'}\n"
    report += f"🖼 <b>Gravatar:</b> <a href=\"{data['gravatar']}\">Проверить</a>\n"

    if breach_data:
        breaches = breach_data.get("breaches", [])
        if breaches:
            report += f"\n🚨 <b>Найдено в {len(breaches)} утечках:</b>\n"
            for b in breaches:
                classes = ", ".join(b.get("data_classes", [])[:3])
                report += f"• <b>{b['name']}</b> ({b['date']})\n"
                report += f"  Данные: {classes}\n"
        else:
            report += f"\n✅ <b>Не найден в известных утечках</b>\n"

        if breach_data.get("error"):
            report += f"\n⚠️ <b>HIBP:</b> {breach_data['error']}\n"

    return report

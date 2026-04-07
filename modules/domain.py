"""Модуль для поиска информации по домену/сайту."""

import re
import logging
import asyncio
import json
from urllib.parse import urlparse

log = logging.getLogger("OSINTBot")


def validate_domain(text: str) -> str | None:
    """Валидирует домен или URL и извлекает домен."""
    text = text.strip().lower()
    # URL -> извлекаем домен
    if text.startswith(("http://", "https://")):
        try:
            parsed = urlparse(text)
            domain = parsed.hostname
        except Exception:
            domain = text.split("/")[2] if "/" in text else None
    else:
        domain = text.split("/")[0] if "/" in text else text

    if not domain:
        return None

    # Проверка формата домена
    if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$", domain):
        return domain
    return None


async def query_dns(domain: str) -> dict:
    """DNS-запросы — A, MX, NS, TXT, SOA записи."""
    result = {"a": [], "mx": [], "ns": [], "txt": [], "soa": None, "cname": None}

    try:
        import dns.asyncresolver
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5

        # A записи
        try:
            answers = await resolver.resolve(domain, "A")
            result["a"] = [str(rdata) for rdata in answers]
        except Exception:
            pass

        # MX записи
        try:
            answers = await resolver.resolve(domain, "MX")
            result["mx"] = [str(rdata.exchange).rstrip(".") for rdata in answers]
        except Exception:
            pass

        # NS записи
        try:
            answers = await resolver.resolve(domain, "NS")
            result["ns"] = [str(rdata).rstrip(".") for rdata in answers]
        except Exception:
            pass

        # TXT записи
        try:
            answers = await resolver.resolve(domain, "TXT")
            result["txt"] = [str(rdata).strip('"')[:200] for rdata in answers]
        except Exception:
            pass

        # SOA запись
        try:
            answers = await resolver.resolve(domain, "SOA")
            if answers:
                result["soa"] = str(answers[0])[:200]
        except Exception:
            pass

        # CNAME
        try:
            answers = await resolver.resolve(domain, "CNAME")
            result["cname"] = str(answers[0].target).rstrip(".")
        except Exception:
            pass

    except ImportError:
        result["_error"] = "dnspython не установлен"
    except Exception as e:
        log.debug(f"DNS query error: {e}")

    return result


async def query_ssl(domain: str) -> dict:
    """SSL-сертификат домена."""
    result = {}
    try:
        import ssl
        import socket

        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                result["subject"] = dict(x[0] for x in cert.get("subject", []))
                result["issuer"] = dict(x[0] for x in cert.get("issuer", []))
                result["version"] = cert.get("version")
                result["serial_number"] = cert.get("serialNumber", "")

                # Даты
                import datetime
                not_before = cert.get("notBefore", "")
                not_after = cert.get("notAfter", "")
                result["valid_from"] = not_before
                result["valid_to"] = not_after

                # SAN (Subject Alternative Names)
                san_list = []
                for ext in cert.get("subjectAltName", []):
                    san_list.append(ext[1])
                result["san"] = san_list[:10]

                # Проверка срока действия
                if not_after:
                    import time
                    expiry = time.mktime(time.strptime(not_after, "%b %d %H:%M:%S %Y %Z"))
                    days_left = int((expiry - time.time()) / 86400)
                    result["days_until_expiry"] = days_left

    except ImportError:
        result["_error"] = "ssl/socket недоступно"
    except Exception as e:
        log.debug(f"SSL query error: {e}")

    return result


async def query_whois_domain(domain: str) -> dict:
    """WHOIS информация о домене."""
    result = {}
    try:
        import httpx
        # Используем бесплатный whois API через веб-сервис
        url = f"https://api.whoisfreaks.com/v1.0/whois?apiKey=free&domain={domain}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "domain": data.get("domain_name", ""),
                    "registrar": data.get("registrar", {}).get("registrar_name", ""),
                    "creation_date": data.get("creation_date", ""),
                    "expiration_date": data.get("expiration_date", ""),
                    "updated_date": data.get("updated_date", ""),
                    "status": data.get("status", []),
                    "name_servers": data.get("name_servers", []),
                    "registrant": {
                        "name": data.get("registrant", {}).get("registrant_name", ""),
                        "org": data.get("registrant", {}).get("registrant_organization", ""),
                        "country": data.get("registrant", {}).get("registrant_country", ""),
                        "email": data.get("registrant", {}).get("registrant_email", ""),
                    } if data.get("registrant") else {},
                }
    except Exception as e:
        log.debug(f"WHOIS error: {e}")

    return result


async def query_wappalyzer(domain: str) -> dict:
    """Определение технологий сайта через Wappalyzer."""
    result = {}
    try:
        import httpx
        # Используем BuiltWith API (бесплатно с ключом)
        import config
        if config.BUILTWITH_API_KEY:
            url = f"https://api.builtwith.com/v21/api.json?KEY={config.BUILTWITH_API_KEY}&LOOKUP={domain}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("Results", [])
                    if results:
                        techs = results[0].get("Result", {}).get("Paths", [{}])[0].get("Technologies", [])
                        result["technologies"] = [
                            {
                                "name": t.get("Name", ""),
                                "category": t.get("Categories", ""),
                                "version": t.get("Version", ""),
                                "description": t.get("Description", ""),
                            }
                            for t in techs[:20]
                        ]
    except Exception as e:
        log.debug(f"Wappalyzer error: {e}")

    return result


async def search_domain_everywhere(domain: str) -> str:
    """Полный поиск по домену с реальными данными."""
    validated = validate_domain(domain)
    if not validated:
        return "❌ Неверный формат домена.\n\nПримеры:\n<code>example.com</code>\n<code>https://example.com</code>"

    # Параллельные запросы
    dns_task = query_dns(validated)
    ssl_task = query_ssl(validated)

    tasks = [dns_task, ssl_task]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    dns_data = results[0] if not isinstance(results[0], Exception) else {}
    ssl_data = results[1] if not isinstance(results[1], Exception) else {}

    # Формируем отчёт
    report = f"🌐 <b>Расширенный поиск по домену</b>\n\n"
    report += f"🔗 <b>Домен:</b> <code>{validated}</code>\n\n"

    # DNS
    if dns_data.get("_error"):
        report += f"⚠️ DNS: {dns_data['_error']}\n\n"
    else:
        report += f"📡 <b>DNS записи:</b>\n"

        if dns_data.get("a"):
            report += f"  🅰 A записи: {', '.join(dns_data['a'][:5])}\n"
        if dns_data.get("cname"):
            report += f"  🔗 CNAME: {dns_data['cname']}\n"
        if dns_data.get("mx"):
            report += f"  📧 MX: {', '.join(dns_data['mx'][:5])}\n"
        if dns_data.get("ns"):
            report += f"  🌐 NS: {', '.join(dns_data['ns'][:5])}\n"
        if dns_data.get("txt"):
            txt_preview = dns_data['txt'][:3]
            for txt in txt_preview:
                # Проверяем SPF, DKIM, DMARC
                if "spf" in txt.lower():
                    report += f"  🛡 SPF: {txt[:100]}...\n"
                elif "dmarc" in txt.lower():
                    report += f"  🛡 DMARC: {txt[:100]}...\n"
                elif "dkim" in txt.lower() or "v=DKIM" in txt:
                    report += f"  🛡 DKIM: {txt[:60]}...\n"
                else:
                    report += f"  📝 TXT: {txt[:80]}...\n"
        if dns_data.get("soa"):
            report += f"  📋 SOA: {dns_data['soa'][:100]}\n"

        report += "\n"

    # SSL
    if ssl_data:
        if ssl_data.get("_error"):
            report += f"⚠️ SSL: {ssl_data['_error']}\n\n"
        else:
            report += f"🔒 <b>SSL-сертификат:</b>\n"

            subject = ssl_data.get("subject", {})
            if subject.get("commonName"):
                report += f"  📝 Выдан для: {subject['commonName']}\n"

            issuer = ssl_data.get("issuer", {})
            if issuer.get("commonName"):
                report += f"  🏢 Выдан кем: {issuer['commonName']}\n"

            if ssl_data.get("valid_from") and ssl_data.get("valid_to"):
                report += f"  📅 Действует: {ssl_data['valid_from']} — {ssl_data['valid_to']}\n"

            if ssl_data.get("days_until_expiry") is not None:
                days = ssl_data["days_until_expiry"]
                if days < 0:
                    report += f"  🚨 Сертификат просрочен! ({abs(days)} дней назад)\n"
                elif days < 30:
                    report += f"  ⚠️ Истекает через {days} дней\n"
                else:
                    report += f"  ✅ Истекает через {days} дней\n"

            san = ssl_data.get("san", [])
            if san:
                report += f"  🌐 Домены в сертификате: {', '.join(san[:5])}"
                if len(san) > 5:
                    report += f" ... и ещё {len(san) - 5}"
                report += "\n"

            report += "\n"

    # Рекомендации
    report += f"🔎 <b>Дополнительные проверки:</b>\n"
    report += f"• <a href=\"https://whois.ru/{validated}\">WHOIS</a>\n"
    report += f"• <a href=\"https://www.shodan.io/host/{validated}\">Shodan</a>\n"
    report += f"• <a href=\"https://censys.io/search?q={validated}\">Censys</a>\n"
    report += f"• <a href=\"https://securitytrails.com/domain/{validated}\">SecurityTrails</a>\n"
    report += f"• <a href=\"https://dnsdumpster.com/\">DNS Dumpster</a>\n"

    report += "\n\n💡 <i>Данные из DNS, SSL и открытых источников</i>"

    return report

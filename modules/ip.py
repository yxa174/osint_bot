"""Модуль для поиска информации по IP-адресу."""

import re
import logging
import asyncio

log = logging.getLogger("OSINTBot")


def validate_ip(text: str) -> str | None:
    """Валидирует IPv4 и IPv6."""
    text = text.strip()
    # IPv4
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", text):
        parts = text.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            return text
    # IPv6
    if re.match(r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$", text):
        return text
    return None


async def query_ip_api(ip: str) -> dict:
    """ip-api.com — геолокация, провайдер, ASN (бесплатно, без ключа)."""
    result = {}
    try:
        import httpx
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting,query"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    result = {
                        "ip": data.get("query", ip),
                        "country": data.get("country", ""),
                        "country_code": data.get("countryCode", ""),
                        "region": data.get("regionName", ""),
                        "city": data.get("city", ""),
                        "zip": data.get("zip", ""),
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "timezone": data.get("timezone", ""),
                        "isp": data.get("isp", ""),
                        "org": data.get("org", ""),
                        "as": data.get("as", ""),
                        "is_mobile": data.get("mobile", False),
                        "is_proxy": data.get("proxy", False),
                        "is_hosting": data.get("hosting", False),
                    }
    except Exception as e:
        log.debug(f"ip-api.com error: {e}")

    return result


async def query_shodan(ip: str, api_key: str) -> dict:
    """Shodan — открытые порты, сервисы, уязвимости."""
    result = {}
    if not api_key:
        return result

    try:
        import httpx
        url = f"https://api.shodan.io/shodan/host/{ip}?key={api_key}&minify=true"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "ports": data.get("ports", []),
                    "org": data.get("org", ""),
                    "isp": data.get("isp", ""),
                    "os": data.get("os", "Unknown"),
                    "hostnames": data.get("hostnames", []),
                    "vulns": data.get("vulns", []),
                    "country": data.get("country_name", ""),
                    "city": data.get("city", ""),
                    "data_count": len(data.get("data", [])),
                }
            elif resp.status_code == 404:
                result["no_data"] = True
    except Exception as e:
        log.debug(f"Shodan error: {e}")

    return result


async def search_ip_everywhere(ip: str) -> str:
    """Полный поиск по IP с реальными данными."""
    validated = validate_ip(ip)
    if not validated:
        return "❌ Неверный формат IP.\n\nПримеры:\n<code>8.8.8.8</code>\n<code>2001:4860:4860::8888</code>"

    import config

    # Параллельные запросы
    ip_api_task = query_ip_api(validated)
    shodan_task = query_shodan(validated, config.SHODAN_API_KEY) if config.SHODAN_API_KEY else None

    tasks = [ip_api_task]
    if shodan_task:
        tasks.append(shodan_task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    ip_data = results[0] if not isinstance(results[0], Exception) else {}
    shodan_data = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else {}

    # Формируем отчёт
    report = f"🌐 <b>Расширенный поиск по IP</b>\n\n"

    if ip_data:
        report += f"🔢 <b>IP:</b> <code>{ip_data.get('ip', validated)}</code>\n\n"

        report += f"📍 <b>Геолокация:</b>\n"
        report += f"• 🌍 Страна: {ip_data.get('country', 'Не определено')} ({ip_data.get('country_code', '')})\n"
        report += f"• 🏙 Город: {ip_data.get('city', 'Не определено')}\n"
        report += f"• 🗺 Регион: {ip_data.get('region', 'Не определено')}\n"
        if ip_data.get('zip'):
            report += f"• 📮 Почтовый индекс: {ip_data['zip']}\n"

        report += f"\n🌐 <b>Сеть:</b>\n"
        report += f"• 📡 Провайдер: {ip_data.get('isp', 'Не определено')}\n"
        report += f"• 🏢 Организация: {ip_data.get('org', 'Не определено')}\n"
        if ip_data.get('as'):
            report += f"• 🔗 AS: {ip_data['as']}\n"
        report += f"• 🕐 Часовой пояс: {ip_data.get('timezone', 'Не определено')}\n"

        # Координаты
        if ip_data.get('lat') and ip_data.get('lon'):
            report += f"• 📍 Координаты: {ip_data['lat']}, {ip_data['lon']}\n"

        # Тип подключения
        report += f"\n📱 <b>Тип подключения:</b>\n"
        mobile = ip_data.get('is_mobile', False)
        proxy = ip_data.get('is_proxy', False)
        hosting = ip_data.get('is_hosting', False)

        if mobile:
            report += f"  📱 Мобильный интернет: Да\n"
        if proxy:
            report += f"  🔒 Прокси/VPN: Да\n"
        if hosting:
            report += f"  🖥 Хостинг/дата-центр: Да\n"
        if not mobile and not proxy and not hosting:
            report += f"  🏠 Домашний интернет\n"

        # Опасности
        risk_items = []
        if proxy:
            risk_items.append("🔒 Прокси/VPN")
        if hosting:
            risk_items.append("🖥 Хостинг")

        if risk_items:
            report += f"\n⚠️ <b>Флаги:</b> {', '.join(risk_items)}\n"
        else:
            report += f"\n✅ <b>Флагов нет</b>\n"

    if shodan_data:
        if shodan_data.get("no_data"):
            report += f"\n🔍 <b>Shodan:</b> Нет данных\n"
        else:
            report += f"\n🔍 <b>Shodan:</b>\n"
            report += f"  🖥 Организация: {shodan_data.get('org', '')}\n"
            report += f"  📡 ISP: {shodan_data.get('isp', '')}\n"
            report += f"  💻 ОС: {shodan_data.get('os', 'Unknown')}\n"

            ports = shodan_data.get('ports', [])
            if ports:
                report += f"  🔓 Открытые порты ({len(ports)}): {', '.join(str(p) for p in ports[:15])}"
                if len(ports) > 15:
                    report += f" ... и ещё {len(ports) - 15}"
                report += "\n"

            hostnames = shodan_data.get('hostnames', [])
            if hostnames:
                report += f"  🌐 Хостнеймы: {', '.join(hostnames[:5])}\n"

            vulns = shodan_data.get('vulns', [])
            if vulns:
                report += f"  🚨 Уязвимости ({len(vulns)}): {', '.join(vulns[:10])}\n"

            report += f"  📊 Записей: {shodan_data.get('data_count', 0)}\n"

    report += "\n\n💡 <i>Данные из ip-api.com и Shodan</i>"

    return report

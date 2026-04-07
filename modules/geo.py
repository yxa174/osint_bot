"""Модуль для поиска по геолокации (координаты/адрес)."""

import re
import logging
import asyncio
from urllib.parse import quote

log = logging.getLogger("OSINTBot")


def validate_coords(text: str) -> tuple[float, float] | None:
    """Извлекает координаты из текста."""
    # Широта, Долгота
    pattern = r"(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)"
    match = re.search(pattern, text.strip())
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return (lat, lon)
    return None


async def query_nominatim_reverse(lat: float, lon: float) -> dict:
    """Nominatim — обратное геокодирование (адрес по координатам)."""
    result = {}
    try:
        import httpx
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&accept-language=ru"
        headers = {"User-Agent": "OSINT-Bot/1.0"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "display_name": data.get("display_name", ""),
                    "address": data.get("address", {}),
                    "type": data.get("type", ""),
                    "category": data.get("category", ""),
                    "osm_type": data.get("osm_type", ""),
                    "osm_id": data.get("osm_id", ""),
                    "boundingbox": data.get("boundingbox", []),
                }
    except Exception as e:
        log.debug(f"Nominatim error: {e}")

    return result


async def query_timezone(lat: float, lon: float) -> dict:
    """Определение часового пояса по координатам."""
    result = {}
    try:
        import httpx
        url = f"https://timezonedb.com/v2.1/get-time-zone?key=demo&format=json&by=position&lat={lat}&lng={lon}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "zone": data.get("zoneName", ""),
                    "gmt_offset": data.get("gmtOffset", 0),
                    "dst": data.get("dst", 0),
                    "formatted_time": data.get("formatted", ""),
                }
    except Exception as e:
        log.debug(f"TimezoneDB error: {e}")

    return result


async def query_nearby(lat: float, lon: float, radius: int = 1000) -> dict:
    """Поиск объектов рядом через Overpass API."""
    result = {"amenities": [], "total": 0}
    try:
        import httpx
        query = f"""
        [out:json][timeout:10];
        (
          node["amenity"](around:{radius},{lat},{lon});
          way["amenity"](around:{radius},{lat},{lon});
        );
        out center;
        """
        url = "https://overpass-api.de/api/interpreter"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, data={"data": query})
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])[:20]
                amenities = {}
                for elem in elements:
                    tags = elem.get("tags", {})
                    amenity = tags.get("amenity", "")
                    if amenity:
                        name = tags.get("name", "Без названия")
                        if amenity not in amenities:
                            amenities[amenity] = []
                        amenities[amenity].append(name)

                result["amenities"] = amenities
                result["total"] = len(elements)
    except Exception as e:
        log.debug(f"Overpass error: {e}")

    return result


async def search_geo_everywhere(lat: float, lon: float) -> str:
    """Полный поиск по координатам."""
    # Параллельные запросы
    nominatim_task = query_nominatim_reverse(lat, lon)
    tz_task = query_timezone(lat, lon)
    nearby_task = query_nearby(lat, lon)

    nom_data, tz_data, nearby_data = await asyncio.gather(
        nominatim_task, tz_task, nearby_task, return_exceptions=True
    )
    if isinstance(nom_data, Exception): nom_data = {}
    if isinstance(tz_data, Exception): tz_data = {}
    if isinstance(nearby_data, Exception): nearby_data = {}

    # Формируем отчёт
    report = f"📍 <b>Поиск по геолокации</b>\n\n"
    report += f"🌍 <b>Координаты:</b> {lat:.6f}, {lon:.6f}\n"
    report += f"🔗 <a href=\"https://www.google.com/maps?q={lat},{lon}\">Google Maps</a> | <a href=\"https://yandex.ru/maps/?pt={lon},{lat}&z=12\">Яндекс.Карты</a>\n\n"

    # Адрес
    if nom_data.get("display_name"):
        report += f"🏠 <b>Адрес:</b> {nom_data['display_name']}\n\n"
        addr = nom_data.get("address", {})
        if addr:
            report += f"📋 <b>Детали адреса:</b>\n"
            for key in ["road", "house_number", "suburb", "city", "state", "postcode", "country"]:
                if addr.get(key):
                    key_ru = {
                        "road": "Улица", "house_number": "Дом", "suburb": "Район",
                        "city": "Город", "state": "Регион", "postcode": "Индекс", "country": "Страна"
                    }.get(key, key)
                    report += f"  {key_ru}: {addr[key]}\n"
            report += "\n"

        report += f"📝 <b>Тип:</b> {nom_data.get('category', '')} / {nom_data.get('type', '')}\n"
        report += f"🗂 <b>OSM ID:</b> {nom_data.get('osm_type', '')} {nom_data.get('osm_id', '')}\n\n"

    # Часовой пояс
    if tz_data.get("zone"):
        report += f"🕐 <b>Часовой пояс:</b> {tz_data['zone']}\n"
        gmt = tz_data.get("gmt_offset", 0)
        gmt_str = f"UTC+{gmt}" if gmt >= 0 else f"UTC{gmt}"
        report += f"  GMT: {gmt_str}\n"
        if tz_data.get("formatted_time"):
            report += f"  Текущее время: {tz_data['formatted_time']}\n"
        report += "\n"

    # Объекты рядом
    if nearby_data.get("amenities"):
        amenities = nearby_data["amenities"]
        total = nearby_data["total"]
        report += f"🏪 <b>Объекты рядом ({total}):</b>\n"

        amenity_ru = {
            "restaurant": "🍽 Ресторан", "cafe": "☕ Кафе", "bar": "🍸 Бар",
            "hospital": "🏥 Больница", "pharmacy": "💊 Аптека", "school": "🏫 Школа",
            "university": "🎓 Университет", "police": "🚔 Полиция", "fire_station": "🚒 Пожарная",
            "bank": "🏦 Банк", "atm": "🏧 Банкомат", "post_office": "📬 Почта",
            "fuel": "⛽ Заправка", "parking": "🅿 Парковка", "hotel": "🏨 Отель",
            "cinema": "🎬 Кинотеатр", "theatre": "🎭 Театр", "supermarket": "🛒 Супермаркет",
            "marketplace": "🏪 Рынок", "library": "📚 Библиотека",
        }

        for amenity, places in list(amenities.items())[:10]:
            icon = amenity_ru.get(amenity, "📍")
            places_str = ", ".join(places[:3])
            report += f"  {icon} {amenity}: {places_str}\n"

        if total > 20:
            report += f"  ... и ещё {total - 20} объектов\n"
    else:
        report += f"🏪 <b>Объекты рядом:</b> Не найдено\n"

    report += "\n\n💡 <i>Данные из OpenStreetMap, Nominatim, Overpass</i>"

    return report

"""Модуль для извлечения EXIF-метаданных из фотографий."""

import re
import logging
import io

log = logging.getLogger("OSINTBot")


def validate_image_url(text: str) -> str | None:
    """Проверяет URL изображения."""
    text = text.strip()
    if re.match(r"https?://[^\s]+\.(jpg|jpeg|png|tiff|webp|heic|bmp|gif)(\?.*)?$", text, re.IGNORECASE):
        return text
    if re.match(r"https?://[^\s]+", text):
        return text
    return None


async def extract_exif_from_url(image_url: str) -> dict:
    """Извлекает EXIF-данные из изображения по URL."""
    result = {}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(image_url)
            if resp.status_code == 200:
                result = extract_exif_from_bytes(resp.content)
    except Exception as e:
        log.debug(f"Image download error: {e}")
        result["_error"] = f"Не удалось загрузить изображение: {e}"

    return result


def extract_exif_from_bytes(data: bytes) -> dict:
    """Извлекает EXIF из байтов изображения."""
    result = {}

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        img = Image.open(io.BytesIO(data))

        # Базовая информация
        result["format"] = img.format or "Не определено"
        result["mode"] = img.mode or "Не определено"
        result["size"] = f"{img.width}x{img.height}"
        result["width"] = img.width
        result["height"] = img.height

        # EXIF
        if hasattr(img, "_getexif") and img._getexif():
            exif_data = img._getexif()
            exif_dict = {}

            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_dict[tag] = value

            # Камера
            if exif_dict.get("Make"):
                result["camera_make"] = exif_dict["Make"]
            if exif_dict.get("Model"):
                result["camera_model"] = exif_dict["Model"]

            # Настройки съёмки
            if exif_dict.get("ExposureTime"):
                exp = exif_dict["ExposureTime"]
                if isinstance(exp, (int, float)):
                    result["exposure"] = f"1/{int(1/exp)}s" if exp < 1 else f"{exp}s"
            if exif_dict.get("FNumber"):
                fnum = exif_dict["FNumber"]
                if isinstance(fnum, (int, float)):
                    result["aperture"] = f"f/{fnum:.1f}"
            if exif_dict.get("ISOSpeedRatings"):
                result["iso"] = exif_dict["ISOSpeedRatings"]
            if exif_dict.get("FocalLength"):
                fl = exif_dict["FocalLength"]
                if isinstance(fl, (int, float)):
                    result["focal_length"] = f"{fl:.1f}mm"

            # Дата съёмки
            if exif_dict.get("DateTimeOriginal"):
                result["date_taken"] = exif_dict["DateTimeOriginal"]
            elif exif_dict.get("DateTime"):
                result["date_taken"] = exif_dict["DateTime"]

            # Программное обеспечение
            if exif_dict.get("Software"):
                result["software"] = exif_dict["Software"]

            # Вспышка
            if exif_dict.get("Flash"):
                flash = exif_dict["Flash"]
                result["flash"] = "Включалась" if flash & 1 else "Не включалась"

            # Ориентация
            if exif_dict.get("Orientation"):
                orient_map = {
                    1: "Нормальная", 3: "Повёрнута на 180°",
                    6: "Повёрнута на 90° CW", 8: "Повёрнута на 90° CCW"
                }
                result["orientation"] = orient_map.get(exif_dict["Orientation"], "Неизвестно")

            # GPS координаты
            if exif_dict.get("GPSInfo"):
                gps = exif_dict["GPSInfo"]
                result["gps"] = extract_gps(gps)

            # Lens
            if exif_dict.get("LensModel"):
                result["lens"] = exif_dict["LensModel"]

        # Если нет EXIF
        if not any(k not in ("_error") for k in result):
            result["no_exif"] = True
            result["format"] = img.format or "Не определено"
            result["size"] = f"{img.width}x{img.height}"

    except ImportError:
        result["_error"] = "PIL (Pillow) не установлен. pip install Pillow"
    except Exception as e:
        log.debug(f"EXIF extraction error: {e}")
        result["_error"] = f"Ошибка извлечения EXIF: {e}"

    return result


def extract_gps(gps_info: dict) -> dict:
    """Извлекает GPS-координаты из EXIF GPSInfo."""
    from PIL.ExifTags import GPSTAGS

    result = {}

    for key, val in gps_info.items():
        tag = GPSTAGS.get(key, key)
        result[tag] = val

    lat = None
    lon = None

    # Широта
    if result.get("GPSLatitude") and result.get("GPSLatitudeRef"):
        dms = result["GPSLatitude"]
        ref = result["GPSLatitudeRef"]
        degrees = dms[0]
        minutes = dms[1]
        seconds = dms[2]
        lat = degrees + minutes / 60 + seconds / 3600
        if ref == "S":
            lat = -lat

    # Долгота
    if result.get("GPSLongitude") and result.get("GPSLongitudeRef"):
        dms = result["GPSLongitude"]
        ref = result["GPSLongitudeRef"]
        degrees = dms[0]
        minutes = dms[1]
        seconds = dms[2]
        lon = degrees + minutes / 60 + seconds / 3600
        if ref == "W":
            lon = -lon

    if lat is not None and lon is not None:
        result["coordinates"] = f"{lat:.6f}, {lon:.6f}"
        result["maps_link"] = f"https://www.google.com/maps?q={lat},{lon}"
        result["yandex_link"] = f"https://yandex.ru/maps/?pt={lon},{lat}&z=15"

    if result.get("GPSAltitude"):
        alt = result["GPSAltitude"]
        result["altitude"] = f"{alt}м"

    return result


def format_exif_report(exif_data: dict) -> str:
    """Формирует отчёт по EXIF-данным."""
    if exif_data.get("_error"):
        return f"❌ {exif_data['_error']}"

    report = f"📷 <b>EXIF-метаданные</b>\n\n"

    if exif_data.get("no_exif"):
        report += f"ℹ️ <b>Метаданные отсутствуют</b>\n"
        report += f"📝 Формат: {exif_data.get('format', 'Не определено')}\n"
        report += f"📐 Размер: {exif_data.get('size', 'Не определено')}\n"
        report += f"\n💡 <i>Метаданные могли быть удалены мессенджером или соцсетью</i>"
        return report

    # Изображение
    report += f"📐 <b>Изображение:</b>\n"
    report += f"• Формат: {exif_data.get('format', 'Не определено')}\n"
    report += f"• Размер: {exif_data.get('size', 'Не определено')}\n"
    report += f"• Режим: {exif_data.get('mode', 'Не определено')}\n"
    if exif_data.get("orientation"):
        report += f"• Ориентация: {exif_data['orientation']}\n"

    # Камера
    camera_parts = []
    if exif_data.get("camera_make"):
        camera_parts.append(exif_data["camera_make"])
    if exif_data.get("camera_model"):
        camera_parts.append(exif_data["camera_model"])
    if camera_parts:
        report += f"\n📸 <b>Камера:</b>\n"
        report += f"• {' '.join(camera_parts)}\n"
    if exif_data.get("lens"):
        report += f"• Объектив: {exif_data['lens']}\n"

    # Настройки
    settings = []
    if exif_data.get("exposure"):
        settings.append(f"Выдержка: {exif_data['exposure']}")
    if exif_data.get("aperture"):
        settings.append(f"Диафрагма: {exif_data['aperture']}")
    if exif_data.get("iso"):
        settings.append(f"ISO: {exif_data['iso']}")
    if exif_data.get("focal_length"):
        settings.append(f"Фокус: {exif_data['focal_length']}")

    if settings:
        report += f"\n⚙️ <b>Настройки съёмки:</b>\n"
        for s in settings:
            report += f"• {s}\n"

    if exif_data.get("flash"):
        report += f"• Вспышка: {exif_data['flash']}\n"

    # Дата
    if exif_data.get("date_taken"):
        report += f"\n📅 <b>Дата съёмки:</b> {exif_data['date_taken']}\n"

    # Софт
    if exif_data.get("software"):
        report += f"💻 <b>Программа:</b> {exif_data['software']}\n"

    # GPS
    if exif_data.get("gps"):
        gps = exif_data["gps"]
        report += f"\n📍 <b>GPS-координаты:</b>\n"
        if gps.get("coordinates"):
            report += f"  🌍 {gps['coordinates']}\n"
        if gps.get("maps_link"):
            report += f"  🗺 <a href=\"{gps['maps_link']}\">Google Maps</a> | <a href=\"{gps.get('yandex_link', '')}\">Яндекс</a>\n"
        if gps.get("GPSAltitude"):
            report += f"  🏔 Высота: {gps['GPSAltitude']}\n"
        if gps.get("GPSProcessingMethod"):
            report += f"  📡 Метод: {gps['GPSProcessingMethod']}\n"

    report += "\n💡 <i>Метаданные извлечены из файла изображения</i>"

    return report


async def search_exif_everywhere(image_source: str) -> str:
    """Полный поиск EXIF из URL."""
    url = validate_image_url(image_source)
    if not url:
        return "❌ Отправьте URL изображения.\n\nПример: <code>https://example.com/photo.jpg</code>"

    exif_data = await extract_exif_from_url(url)
    return format_exif_report(exif_data)

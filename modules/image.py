"""Модуль для обратного поиска изображений."""

import logging

log = logging.getLogger("OSINTBot")


def generate_image_search_links(image_url: str) -> list[dict]:
    """Генерирует ссылки для обратного поиска по изображению."""
    from urllib.parse import quote

    encoded_url = quote(image_url, safe="")

    links = [
        {
            "platform": "Google Images",
            "url": f"https://lens.google.com/uploadbyurl?url={encoded_url}",
            "icon": "🔍",
        },
        {
            "platform": "Yandex Картинки",
            "url": f"https://yandex.ru/images/search?rpt=imageview&url={encoded_url}",
            "icon": "🟡",
        },
        {
            "platform": "TinEye",
            "url": f"https://tineye.com/search/?url={encoded_url}",
            "icon": "👁",
        },
        {
            "platform": "Bing Visual Search",
            "url": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{encoded_url}",
            "icon": "🔎",
        },
        {
            "platform": "PimEyes (лица)",
            "url": "https://pimeyes.com/en",
            "icon": "👤",
        },
    ]

    return links


def format_image_report(image_url: str) -> str:
    """Формирует отчёт по обратному поиску изображения."""
    report = f"📷 <b>Обратный поиск изображения</b>\n\n"
    report += f"🔗 <b>URL:</b> <code>{image_url[:80]}...</code>\n\n"
    report += "🔍 <b>Поисковые системы:</b>\n\n"

    links = generate_image_search_links(image_url)
    for link in links:
        report += f"{link['icon']} <a href=\"{link['url']}\">{link['platform']}</a>\n"

    report += "\n💡 <i>Нажмите на ссылку для поиска похожих изображений</i>"

    return report

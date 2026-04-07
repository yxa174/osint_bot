"""OSINT Telegram Bot — полный поиск из реальных источников."""

import logging
import re
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

import config
from modules.phone import search_phone_everywhere, validate_phone
from modules.username import search_username, format_username_report, validate_username
from modules.email import search_email_everywhere, validate_email
from modules.name import search_name_everywhere, validate_name
from modules.car import search_car_everywhere, validate_plate, validate_vin
from modules.ip import search_ip_everywhere, validate_ip
from modules.domain import search_domain_everywhere, validate_domain
from modules.crypto import search_crypto_everywhere, detect_crypto_address
from modules.geo import search_geo_everywhere, validate_coords
from modules.exif import search_exif_everywhere

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("osint_bot.log")],
)
log = logging.getLogger("OSINTBot")

HISTORY_FILE = "history.json"
HELP_TEXT = """🔍 <b>OSINT Bot — полный поиск</b>

Бот <b>сам собирает данные</b> из API и открытых источников:

📱 <b>Телефон</b> — оператор, регион, мессенджеры, API
👤 <b>Username</b> — 60+ платформ (реальные HTTP-запросы)
📧 <b>Email</b> — репутация, утечки, Gravatar, Hunter
📝 <b>ФИО</b> — DuckDuckGo, Wikipedia RU/EN
🚗 <b>Авто</b> — NHTSA VIN-декодер, регион по госномеру
🌐 <b>IP</b> — геолокация, провайдер, Shodan
� <b>Домен</b> — DNS, SSL, технологии
₿ <b>Крипто</b> — BTC/ETH/TRX баланс и транзакции
📍 <b>Геолокация</b> — адрес, объекты рядом (координаты)
📷 <b>Фото (URL)</b> — EXIF-метаданные, GPS

📜 <b>Команды:</b>
/history — история запросов
/stats — статистика бота
/clear — очистить историю

💡 <i>Просто выберите тип и отправьте данные!</i>"""


def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📱 Телефон", callback_data="search_phone"),
            InlineKeyboardButton("👤 Username", callback_data="search_username"),
        ],
        [
            InlineKeyboardButton("📧 Email", callback_data="search_email"),
            InlineKeyboardButton("📝 ФИО", callback_data="search_name"),
        ],
        [
            InlineKeyboardButton("🚗 Авто", callback_data="search_car"),
            InlineKeyboardButton("🌐 IP", callback_data="search_ip"),
        ],
        [
            InlineKeyboardButton("� Домен", callback_data="search_domain"),
            InlineKeyboardButton("₿ Крипто", callback_data="search_crypto"),
        ],
        [
            InlineKeyboardButton("📍 Геолокация", callback_data="search_geo"),
            InlineKeyboardButton("�📷 Фото", callback_data="search_image"),
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_history(history: dict):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Save history error: {e}")


def add_to_history(user_id: int, username: str, search_type: str, query: str, result_preview: str):
    history = load_history()
    user_key = str(user_id)
    if user_key not in history:
        history[user_key] = []

    history[user_key].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,
        "type": search_type,
        "query": query[:100],
        "result_preview": result_preview[:100],
    })

    # Ограничиваем историю (100 записей на пользователя)
    history[user_key] = history[user_key][-100:]
    save_history(history)


def get_stats() -> dict:
    history = load_history()
    stats = {"total": 0, "users": len(history), "by_type": {}, "recent": []}

    for user_key, entries in history.items():
        for entry in entries:
            stats["total"] += 1
            t = entry.get("type", "unknown")
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            stats["recent"].append(entry)

    stats["recent"] = sorted(stats["recent"], key=lambda x: x["time"], reverse=True)[:10]
    return stats


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"Пользователь {user.id} (@{user.username}) запустил бота")
    await update.message.reply_text(
        HELP_TEXT, reply_markup=get_main_keyboard(),
        parse_mode="HTML", disable_web_page_preview=True,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_TEXT, reply_markup=get_main_keyboard(),
        parse_mode="HTML", disable_web_page_preview=True,
    )


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = load_history()
    entries = history.get(str(user_id), [])

    if not entries:
        await update.message.reply_text("📜 История пуста. Сделайте первый поиск!")
        return

    entries = entries[-10:][::-1]  # Последние 10, новые сверху
    text = f"📜 <b>История запросов</b> (последние {len(entries)}):\n\n"
    for i, entry in enumerate(entries, 1):
        type_emoji = {
            "phone": "📱", "username": "👤", "email": "📧",
            "name": "📝", "car": "🚗", "ip": "🌐",
            "domain": "🔗", "crypto": "₿", "geo": "📍",
            "image": "📷",
        }.get(entry["type"], "🔍")
        text += f"{i}. {type_emoji} [{entry['time']}] {entry['query'][:40]}\n"

    keyboard = [[InlineKeyboardButton("🗑 Очистить", callback_data="clear_history")]]
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()
    type_names = {
        "phone": "📱 Телефон", "username": "👤 Username",
        "email": "📧 Email", "name": "📝 ФИО", "car": "🚗 Авто",
        "ip": "🌐 IP", "domain": "🔗 Домен", "crypto": "₿ Крипто",
        "geo": "📍 Геолокация", "image": "📷 Фото",
    }

    text = f"📊 <b>Статистика бота</b>\n\n"
    text += f"🔢 Всего запросов: {stats['total']}\n"
    text += f"👥 Пользователей: {stats['users']}\n\n"
    text += f"<b>По типам:</b>\n"
    for t, count in sorted(stats["by_type"].items(), key=lambda x: x[1], reverse=True):
        name = type_names.get(t, t)
        text += f"• {name}: {count}\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = load_history()
    if str(user_id) in history:
        del history[str(user_id)]
        save_history(history)
        await update.callback_query.answer("✅ История очищена")
        await update.callback_query.edit_message_text("✅ История запросов очищена")
    else:
        await update.callback_query.answer("История уже пуста")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "help":
        await query.edit_message_text(
            HELP_TEXT, reply_markup=get_main_keyboard(),
            parse_mode="HTML", disable_web_page_preview=True,
        )
    elif action == "clear_history":
        await clear_history(update, context)
    elif action.startswith("search_"):
        search_type = action.replace("search_", "")
        prompts = {
            "phone": "📱 <b>Поиск по телефону</b>\n\nОтправьте номер:\n<code>+79991234567</code>",
            "username": "👤 <b>Поиск по username</b>\n\nОтправьте никнейм:\n<code>durov</code>",
            "email": "📧 <b>Поиск по email</b>\n\nОтправьте email:\n<code>user@gmail.com</code>",
            "name": "📝 <b>Поиск по ФИО</b>\n\nОтправьте ФИО:\n<code>Иванов Иван Иванович</code>",
            "car": "🚗 <b>Поиск по авто</b>\n\nОтправьте госномер или VIN:\n<code>А123БВ777</code>\n<code>XTA210930Y2618055</code>",
            "ip": "🌐 <b>Поиск по IP</b>\n\nОтправьте IP-адрес:\n<code>8.8.8.8</code>",
            "domain": "🔗 <b>Поиск по домену</b>\n\nОтправьте домен или URL:\n<code>example.com</code>",
            "crypto": "₿ <b>Поиск по криптокошельку</b>\n\nОтправьте адрес:\n<code>1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</code>\n<code>0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe</code>",
            "geo": "� <b>Поиск по геолокации</b>\n\nОтправьте координаты:\n<code>55.7558, 37.6173</code>",
            "image": "📷 <b>EXIF фото</b>\n\nОтправьте URL изображения:\n<code>https://example.com/photo.jpg</code>",
        }
        prompt = prompts.get(search_type, "Выберите тип поиска:")
        context.user_data["pending_search"] = search_type

        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data="help")]]
        await query.edit_message_text(
            prompt, reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    search_type = context.user_data.get("pending_search")

    if not search_type:
        await update.message.reply_text(
            "⚠️ Сначала выберите тип поиска в меню.",
            reply_markup=get_main_keyboard(),
        )
        return

    log.info(f"Поиск ({search_type}): {text}")
    msg = await update.message.reply_text("⏳ Собираю данные...")

    try:
        handler_map = {
            "phone": handle_phone_search,
            "username": handle_username_search,
            "email": handle_email_search,
            "name": handle_name_search,
            "car": handle_car_search,
            "ip": handle_ip_search,
            "domain": handle_domain_search,
            "crypto": handle_crypto_search,
            "geo": handle_geo_search,
            "image": handle_image_search,
        }

        handler = handler_map.get(search_type)
        if handler:
            result = await handler(text)
        else:
            result = "❌ Неизвестный тип поиска."

        # Сохраняем в историю
        query_preview = text[:50]
        result_preview = re.sub(r"<[^>]+>", "", result)[:100]
        add_to_history(
            update.effective_user.id,
            update.effective_user.username or str(update.effective_user.id),
            search_type, query_preview, result_preview
        )

        # Разбиваем длинные сообщения
        if len(result) > 4000:
            chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
            for chunk in chunks[:-1]:
                await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
            await msg.edit_text(chunks[-1], parse_mode="HTML", disable_web_page_preview=True)
        else:
            await msg.edit_text(result, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        log.error(f"Ошибка ({search_type}): {e}")
        await msg.edit_text(
            f"❌ Ошибка:\n<code>{str(e)}</code>\n\nПопробуйте позже.",
            parse_mode="HTML",
        )

    context.user_data.pop("pending_search", None)


async def handle_phone_search(text): return await search_phone_everywhere(text)
async def handle_username_search(text):
    username = validate_username(text)
    if not username:
        return "❌ Неверный формат username.\n\nПример: <code>durov</code>"
    return format_username_report(await search_username(username))
async def handle_email_search(text): return await search_email_everywhere(text)
async def handle_name_search(text):
    data = validate_name(text)
    return await search_name_everywhere(data) if data else "❌ Неверный формат.\n\nПример: <code>Иванов Иван Иванович</code>"
async def handle_car_search(text):
    plate, vin = validate_plate(text), validate_vin(text)
    return await search_car_everywhere(plate, vin) if (plate or vin) else "❌ Неверный формат.\n\nПример: <code>А123БВ777</code> или <code>XTA210930Y2618055</code>"
async def handle_ip_search(text): return await search_ip_everywhere(text) if validate_ip(text) else "❌ Неверный формат IP.\n\nПример: <code>8.8.8.8</code>"
async def handle_domain_search(text): return await search_domain_everywhere(text) if validate_domain(text) else "❌ Неверный формат домена.\n\nПример: <code>example.com</code>"
async def handle_crypto_search(text): return await search_crypto_everywhere(text) if detect_crypto_address(text) else "❌ Не распознан криптокошелёк."
async def handle_geo_search(text):
    coords = validate_coords(text)
    return await search_geo_everywhere(*coords) if coords else "❌ Неверный формат.\n\nПример: <code>55.7558, 37.6173</code>"
def handle_image_search(text): return search_exif_everywhere(text)


def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_telegram_bot_token_here":
        log.error("❌ Укажите BOT_TOKEN в .env!")
        return

    log.info("🚀 Запуск OSINT Bot...")

    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("history", history_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

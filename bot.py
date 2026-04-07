"""OSINT Telegram Bot — поиск данных из реальных источников."""

import logging
import re
import asyncio
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
from modules.image import format_image_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("osint_bot.log")],
)
log = logging.getLogger("OSINTBot")

HELP_TEXT = """🔍 <b>OSINT Bot — поиск из реальных источников</b>

Бот <b>сам собирает данные</b> из API и открытых источников:

📱 <b>Телефон</b> — оператор, регион, мессенджеры, API-данные
👤 <b>Username</b> — проверка на 60+ платформах (реальные HTTP-запросы)
📧 <b>Email</b> — репутация, утечки HIBP, Gravatar, Hunter.io, EmailRep
📝 <b>ФИО</b> — DuckDuckGo, Wikipedia (RU/EN), транслитерация
🚗 <b>Авто</b> — VIN-декодер (NHTSA), регион по госномеру
📷 <b>Фото (URL)</b> — ссылки на обратный поиск

<b>Форматы:</b>
• Телефон: +79991234567
• Username: durov
• Email: user@gmail.com
• ФИО: Иванов Иван Иванович
• Авто: А123БВ777 или XTA210930Y2618055
• Фото: https://example.com/photo.jpg"""


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
            InlineKeyboardButton("📷 Фото", callback_data="search_image"),
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "help":
        await query.edit_message_text(
            HELP_TEXT, reply_markup=get_main_keyboard(),
            parse_mode="HTML", disable_web_page_preview=True,
        )
    elif action.startswith("search_"):
        search_type = action.replace("search_", "")
        prompts = {
            "phone": "📱 <b>Поиск по телефону</b>\n\nОтправьте номер:\n<code>+79991234567</code>",
            "username": "👤 <b>Поиск по username</b>\n\nОтправьте никнейм:\n<code>durov</code>",
            "email": "📧 <b>Поиск по email</b>\n\nОтправьте email:\n<code>user@gmail.com</code>",
            "name": "📝 <b>Поиск по ФИО</b>\n\nОтправьте ФИО:\n<code>Иванов Иван Иванович</code>",
            "car": "🚗 <b>Поиск по авто</b>\n\nОтправьте госномер или VIN:\n<code>А123БВ777</code>\n<code>XTA210930Y2618055</code>",
            "image": "📷 <b>Поиск по фото</b>\n\nОтправьте URL:\n<code>https://example.com/photo.jpg</code>",
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
    msg = await update.message.reply_text("⏳ Выполняется поиск, собираю данные...")

    try:
        if search_type == "phone":
            result = await handle_phone_search(text)
        elif search_type == "username":
            result = await handle_username_search(text)
        elif search_type == "email":
            result = await handle_email_search(text)
        elif search_type == "name":
            result = await handle_name_search(text)
        elif search_type == "car":
            result = await handle_car_search(text)
        elif search_type == "image":
            result = handle_image_search(text)
        else:
            result = "❌ Неизвестный тип поиска."

        # Разбиваем длинные сообщения
        if len(result) > 4000:
            for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
                await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await msg.edit_text(result, parse_mode="HTML", disable_web_page_preview=True)

        log.info(f"Успешный поиск ({search_type}) для пользователя {update.effective_user.id}")

    except Exception as e:
        log.error(f"Ошибка при поиске ({search_type}): {e}")
        await msg.edit_text(
            f"❌ Произошла ошибка:\n<code>{str(e)}</code>\n\nПопробуйте позже.",
            parse_mode="HTML",
        )

    context.user_data.pop("pending_search", None)


async def handle_phone_search(text: str) -> str:
    return await search_phone_everywhere(text)


async def handle_username_search(text: str) -> str:
    username = validate_username(text)
    if not username:
        return "❌ Неверный формат username.\n\nДопустимы: буквы, цифры, _ (3-50 символов)\nПример: <code>durov</code>"

    result = await search_username(username)
    return format_username_report(result)


async def handle_email_search(text: str) -> str:
    return await search_email_everywhere(text)


async def handle_name_search(text: str) -> str:
    name_data = validate_name(text)
    if not name_data:
        return "❌ Неверный формат.\n\nПример: <code>Иванов Иван Иванович</code>"
    return await search_name_everywhere(name_data)


async def handle_car_search(text: str) -> str:
    plate = validate_plate(text)
    vin = validate_vin(text)

    if not plate and not vin:
        return "❌ Неверный формат.\n\nПримеры:\n<code>А123БВ777</code> (госномер)\n<code>XTA210930Y2618055</code> (VIN)"

    return await search_car_everywhere(plate, vin)


def handle_image_search(text: str) -> str:
    url_pattern = r"https?://[^\s]+"
    match = re.search(url_pattern, text)
    if not match:
        return "❌ Отправьте URL изображения.\n\nПример: <code>https://example.com/photo.jpg</code>"
    return format_image_report(match.group(0))


def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_telegram_bot_token_here":
        log.error("❌ Укажите BOT_TOKEN в .env файле!")
        return

    log.info("🚀 Запуск OSINT Bot...")

    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("✅ Бот запущен и ожидает сообщения...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

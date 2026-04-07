"""OSINT Telegram Bot — поиск информации по открытым источникам."""

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config
from modules.phone import format_phone_report, validate_phone
from modules.username import search_username, format_username_report, validate_username
from modules.email import format_email_report, validate_email, check_email_breaches
from modules.name import format_name_report, validate_name
from modules.image import format_image_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("osint_bot.log")],
)
log = logging.getLogger("OSINTBot")

HELP_TEXT = """🔍 <b>OSINT Bot — поиск по открытым источникам</b>

Выберите тип поиска или отправьте данные напрямую:

📱 <b>Телефон</b> — информация, оператор, мессенджеры
👤 <b>Username</b> — поиск по соцсетям и платформам
📧 <b>Email</b> — провайдер, утечки, Gravatar
📝 <b>ФИО</b> — ссылки для поиска человека
📷 <b>Фото (URL)</b> — обратный поиск изображения

<b>Форматы:</b>
• Телефон: +79991234567
• Username: durov
• Email: user@gmail.com
• ФИО: Иванов Иван Иванович
• Фото: https://example.com/photo.jpg"""


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с инлайн-кнопками."""
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
            InlineKeyboardButton("📷 Фото (URL)", callback_data="search_image"),
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start."""
    user = update.effective_user
    log.info(f"Пользователь {user.id} (@{user.username}) запустил бота")
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help."""
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий инлайн-кнопок."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "help":
        await query.edit_message_text(
            HELP_TEXT,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    elif action.startswith("search_"):
        search_type = action.replace("search_", "")
        prompts = {
            "phone": "📱 <b>Поиск по телефону</b>\n\nОтправьте номер телефона:\n<code>+79991234567</code>",
            "username": "👤 <b>Поиск по username</b>\n\nОтправьте никнейм:\n<code>durov</code>",
            "email": "📧 <b>Поиск по email</b>\n\nОтправьте email адрес:\n<code>user@gmail.com</code>",
            "name": "📝 <b>Поиск по ФИО</b>\n\nОтправьте ФИО:\n<code>Иванов Иван Иванович</code>",
            "image": "📷 <b>Поиск по фото</b>\n\nОтправьте URL изображения:\n<code>https://example.com/photo.jpg</code>",
        }
        prompt = prompts.get(search_type, "Выберите тип поиска:")
        context.user_data["pending_search"] = search_type

        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="help")],
        ]
        await query.edit_message_text(
            prompt,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений."""
    text = update.message.text.strip()
    search_type = context.user_data.get("pending_search")

    if not search_type:
        await update.message.reply_text(
            "⚠️ Сначала выберите тип поиска в меню.",
            reply_markup=get_main_keyboard(),
        )
        return

    log.info(f"Поиск ({search_type}): {text}")
    await update.message.reply_text("⏳ Выполняется поиск...")

    try:
        if search_type == "phone":
            result = handle_phone_search(text)
        elif search_type == "username":
            result = await handle_username_search(text)
        elif search_type == "email":
            result = await handle_email_search(text)
        elif search_type == "name":
            result = handle_name_search(text)
        elif search_type == "image":
            result = handle_image_search(text)
        else:
            result = "❌ Неизвестный тип поиска."

        # Разбиваем длинные сообщения
        if len(result) > 4000:
            for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
                await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await update.message.reply_text(result, parse_mode="HTML", disable_web_page_preview=True)

        log.info(f"Успешный поиск ({search_type}) для пользователя {update.effective_user.id}")

    except Exception as e:
        log.error(f"Ошибка при поиске ({search_type}): {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка:\n<code>{str(e)}</code>\n\nПопробуйте позже.",
            parse_mode="HTML",
        )

    context.user_data.pop("pending_search", None)


def handle_phone_search(text: str) -> str:
    """Поиск по телефону."""
    phone = validate_phone(text)
    if not phone:
        return "❌ Неверный формат номера.\n\nПример: <code>+79991234567</code>"
    return format_phone_report(phone)


async def handle_username_search(text: str) -> str:
    """Поиск по username."""
    username = validate_username(text)
    if not username:
        return "❌ Неверный формат username.\n\nДопустимы: буквы, цифры, _ (5-32 символа)\nПример: <code>durov</code>"

    result = await search_username(username)
    return format_username_report(result)


async def handle_email_search(text: str) -> str:
    """Поиск по email."""
    email = validate_email(text)
    if not email:
        return "❌ Неверный формат email.\n\nПример: <code>user@gmail.com</code>"

    breach_data = None
    if config.HIBP_API_KEY:
        breach_data = await check_email_breaches(email, config.HIBP_API_KEY)

    return format_email_report(email, breach_data)


def handle_name_search(text: str) -> str:
    """Поиск по ФИО."""
    name_data = validate_name(text)
    if not name_data:
        return "❌ Неверный формат.\n\nПример: <code>Иванов Иван Иванович</code>"
    return format_name_report(name_data)


def handle_image_search(text: str) -> str:
    """Поиск по изображению."""
    url_pattern = r"https?://[^\s]+"
    match = re.search(url_pattern, text)
    if not match:
        return "❌ Отправьте URL изображения.\n\nПример: <code>https://example.com/photo.jpg</code>"
    return format_image_report(match.group(0))


def main():
    """Запуск бота."""
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

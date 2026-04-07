# 🔍 OSINT Telegram Bot

Telegram-бот для поиска информации по открытым источникам (OSINT).

## Возможности

| Тип поиска | Описание |
|---|---|
| 📱 **Телефон** | Страна, оператор, тип номера, ссылки на мессенджеры (TG, WA, Viber) |
| 👤 **Username** | Поиск по 17+ платформам (Telegram, Instagram, GitHub, VK, Twitter/X и др.) |
| 📧 **Email** | Провайдер, проверка на временный email, Gravatar, проверка утечек (HIBP) |
| 📝 **ФИО** | Генерация ссылок для поиска человека в соцсетях и реестрах |
| 📷 **Фото (URL)** | Обратный поиск изображения (Google Lens, Yandex, TinEye) |

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yxa174/osint_bot.git
cd osint_bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте `.env` файл:
```env
BOT_TOKEN=ваш_токен_от_BotFather
HIBP_API_KEY=ваш_ключ_HaveIBeenPwned  # опционально
```

## Получение токенов

### Telegram Bot Token
1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте токен в `.env`

### Have I Been Pwned API Key (опционально)
1. Зарегистрируйтесь на [haveibeenpwned.com/API/Key](https://haveibeenpwned.com/API/Key)
2. Купите API ключ ($3.50/мес)
3. Добавьте в `.env` как `HIBP_API_KEY`

> Без HIBP_API_KEY проверка email на утечки будет недоступна.

## Запуск

```bash
python3 bot.py
```

## Использование

1. Отправьте `/start` боту
2. Выберите тип поиска в меню
3. Отправьте данные в нужном формате

### Форматы данных

| Тип | Пример |
|---|---|
| Телефон | `+79991234567` |
| Username | `durov` |
| Email | `user@gmail.com` |
| ФИО | `Иванов Иван Иванович` |
| Фото | `https://example.com/photo.jpg` |

## Структура проекта

```
osint_bot/
├── bot.py              — основной файл бота
├── config.py           — переменные окружения
├── requirements.txt    — зависимости
├── .gitignore          — игнорируемые файлы
├── README.md           — документация
└── modules/            — модули поиска
    ├── phone.py        — поиск по телефону
    ├── username.py     — поиск по username
    ├── email.py        — поиск по email
    ├── name.py         — поиск по ФИО
    └── image.py        — обратный поиск изображений
```

## Поддерживаемые платформы (Username)

- Telegram, Instagram, TikTok, GitHub
- Twitter/X, YouTube, VK, Facebook
- LinkedIn, Reddit, Pinterest, Twitch
- Steam, SoundCloud, Spotify, Docker Hub
- Codeforces, LeetCode

## Зависимости

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram Bot API
- [phonenumbers](https://github.com/daviddrysdale/python-phonenumbers) — валидация и парсинг телефонов
- [httpx](https://github.com/encode/httpx) — async HTTP
- [python-dotenv](https://github.com/theskumar/python-dotenv) — загрузка `.env`

## Правовая информация

Бот использует **только открытые источники** и предназначен для:
- Исследования собственных цифровых следов
- Проверки контрагентов
- Журналистских расследований

**Не используйте бот для:**
- Сбора персональных данных без согласия
- Преследования или сталкинга
- Нарушения законодательства о персональных данных

## Лицензия

MIT

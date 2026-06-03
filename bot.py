import logging
import asyncio
import random
import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import anthropic

# Tokenlar environment variable dan o'qiladi
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8897001080:AAFdX4IY05mS5ojOUsVVgkpv-tjwYfZz3d4")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "babybantic")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "@babybantic_admin")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Sen "Baby Bantic" bolalar kiyimi va oyoq kiyimi do'konining onlayn maslahatchi xodimiSan.

DO'KON HAQIDA:
- Xitoy va Turkiyaning sifatli, zamonaviy fabrikaviy bolalar kiyimlari
- Bolalar oyoq kiyimlari
- O'zbekiston bo'ylab dostavka xizmati bor
- Narxlar qulay, ko'plab skidkalar mavjud

MUHIM QOIDALAR:
1. HECH QACHON o'zingni bot yoki AI ekanimni aytma - sen do'kon xodimiSan
2. Faqat O'ZBEK tilida javob ber
3. Xushmuomila, iliq, samimiy bo'l - xuddi do'stona xodim kabi
4. Ayollar bilan gaplashayotganda mehr bilan muomala qil
5. Mijozni xarid qilishga undab tur, lekin bosim o'tkazma
6. Qisqa va aniq javob ber
7. Emoji ishlatishi mumkin, lekin ko'p emas
8. Narx so'rashsa kanaldan ma'lumot asosida javob ber, aniq narx bo'lmasa adminga yo'nalt
9. Mijozni ushlab qolish uchun qiziqarli savollar ber

KANAL MA'LUMOTLARI:
{channel_posts}

Agar aniq narx yoki mahsulot ma'lumoti bo'lmasa: "Buning aniq narxi uchun adminga murojaat qiling: {admin}"

Tabiiy, insoniy tarzda javob ber!"""


def get_channel_posts():
    try:
        url = f"https://t.me/s/{CHANNEL_USERNAME}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.texts = []
                    self.capture = False

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    cls = attrs_dict.get('class', '')
                    if 'tgme_widget_message_text' in cls:
                        self.capture = True

                def handle_endtag(self, tag):
                    if tag == 'div':
                        self.capture = False

                def handle_data(self, data):
                    if self.capture and data.strip():
                        self.texts.append(data.strip())

            parser = TextExtractor()
            parser.feed(response.text)
            if parser.texts:
                return "\n".join(parser.texts[-20:])
    except Exception as e:
        logger.error(f"Kanal xatosi: {e}")
    return "Kanal ma'lumotlari mavjud emas"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text or ""

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(random.uniform(2, 4))

    channel_posts = get_channel_posts()
    system = SYSTEM_PROMPT.format(channel_posts=channel_posts, admin=ADMIN_USERNAME)

    if 'history' not in context.user_data:
        context.user_data['history'] = []

    context.user_data['history'].append({"role": "user", "content": user_message})

    if len(context.user_data['history']) > 20:
        context.user_data['history'] = context.user_data['history'][-20:]

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=system,
            messages=context.user_data['history']
        )
        bot_response = response.content[0].text
        context.user_data['history'].append({"role": "assistant", "content": bot_response})

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(random.uniform(1, 2))
        await update.message.reply_text(bot_response)

    except Exception as e:
        logger.error(f"Xato: {e}")
        await update.message.reply_text("Kechirasiz, hozir texnik muammo bor. Biroz kutib qayta yozing 🙏")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(random.uniform(3, 5))

    channel_posts = get_channel_posts()
    system = SYSTEM_PROMPT.format(channel_posts=channel_posts, admin=ADMIN_USERNAME)

    if 'history' not in context.user_data:
        context.user_data['history'] = []

    caption = update.message.caption or ""
    user_message = f"Mijoz rasm yubordi. {caption if caption else 'Narxi qancha deb so`rayapti.'}"
    context.user_data['history'].append({"role": "user", "content": user_message})

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=system,
            messages=context.user_data['history']
        )
        bot_response = response.content[0].text
        context.user_data['history'].append({"role": "assistant", "content": bot_response})
        await asyncio.sleep(random.uniform(1, 2))
        await update.message.reply_text(bot_response)

    except Exception as e:
        logger.error(f"Xato: {e}")
        await update.message.reply_text("Kechirasiz, hozir texnik muammo bor. Biroz kutib qayta yozing 🙏")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("Baby Bantic bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

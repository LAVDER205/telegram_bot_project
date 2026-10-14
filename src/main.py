import asyncio
import os
import json
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update, FSInputFile
from aiogram.filters import Command

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не задан. Проверь .env или переменные окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer("Привет!")


@dp.message()
async def handle_message(message: Message):
    text = message.text

    if text == "Картинка":
        await message.answer_document(FSInputFile("silly_cat.webp"), caption="Котик")
        await message.answer("вот!")


async def handler(event: dict, context):
    body: str = event["body"]
    update_data = json.loads(body) if body else {}

    await dp.feed_update(
        bot,
        Update.model_validate(update_data),
    )
    return {"statusCode": 200, "body": ""}


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

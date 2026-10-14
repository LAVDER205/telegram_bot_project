import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ai_service import extract_text_from_file, generate_article

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- Состояния для сбора материалов ---
class ArticleForm(StatesGroup):
    waiting_for_topic = State()
    waiting_for_files = State()


# --- Хранилище собранных текстов (в памяти, для простоты) ---
user_materials: dict[int, dict] = {}


# --- Команда запуска сбора статьи ---
@dp.message(Command("new_article"))
async def start_article(message: Message, state: FSMContext):
    await state.set_state(ArticleForm.waiting_for_topic)
    await message.answer("📝 Введите тему статьи:")


# --- Получаем тему ---
@dp.message(ArticleForm.waiting_for_topic)
async def get_topic(message: Message, state: FSMContext):
    user_materials[message.from_user.id] = {
        "topic": message.text,
        "texts": [],
        "filenames": [],
    }
    await state.set_state(ArticleForm.waiting_for_files)
    await message.answer(
        "📎 Отправьте файлы с материалами (.txt, .pdf, .docx).\n"
        "Когда закончите — отправьте команду /generate"
    )


# --- Принимаем документы ---
@dp.message(ArticleForm.waiting_for_files, F.document)
async def handle_document(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in user_materials:
        await message.answer("Сначала введите /new_article")
        return

    doc = message.document
    filename = doc.file_name or "unknown"

    # Скачиваем файл
    file = await bot.get_file(doc.file_id)
    file_bytes = await bot.download_file(file.file_path)

    try:
        text = await extract_text_from_file(file_bytes.read(), filename)
        user_materials[user_id]["texts"].append(text)
        user_materials[user_id]["filenames"].append(filename)
        await message.answer(f"✅ Файл «{filename}» принят. Символов: {len(text)}")
    except Exception as e:
        await message.answer(f"⚠️ Не удалось прочитать «{filename}»: {e}")


# --- Запуск генерации ---
@dp.message(ArticleForm.waiting_for_files, Command("generate"))
async def generate(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = user_materials.get(user_id)

    if not data or not data["texts"]:
        await message.answer("Сначала загрузите хотя бы один файл.")
        return

    await state.clear()
    await message.answer("⏳ Генерирую статью, это может занять до минуты...")

    combined_text = "\n\n---\n\n".join(data["texts"])
    result = await generate_article(data["topic"], combined_text)

    # Telegram ограничивает длину сообщения ~4096 символами
    # Разбиваем на части
    max_len = 4000
    if len(result) <= max_len:
        await message.answer(result)
    else:
        for i in range(0, len(result), max_len):
            await message.answer(result[i:i + max_len])

    # Очищаем хранилище
    del user_materials[user_id]


# --- Заглушка для остальных сообщений ---
@dp.message()
async def handle_message(message: Message):
    await message.answer(
        "Я пока умею только собирать статьи из файлов.\n"
        "Нажмите /new_article, чтобы начать."
    )


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

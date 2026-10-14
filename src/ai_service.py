import os
import io
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pypdf import PdfReader
from docx import Document

# Загружаем .env из корня проекта (на две папки выше src/)
# Если структура другая — можно просто load_dotenv()
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY не задан. Проверь .env в корне проекта "
        "или переменные окружения."
    )

# Инициализируем клиент OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# Бесплатная модель. Актуальный список: https://openrouter.ai/models?max_price=0
MODEL_NAME = "openrouter/free"


async def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Извлекает текст из файла в зависимости от его расширения."""
    ext = filename.lower().split('.')[-1]

    if ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")

    elif ext == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif ext == "docx":
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text

    else:
        raise ValueError(f"Неподдерживаемый формат: .{ext}")


async def generate_article(topic: str, combined_text: str) -> str:
    """Отправляет материалы в ИИ и получает готовую статью."""

    # Обрезаем текст, чтобы не превысить контекст бесплатной модели
    max_chars = 12000
    if len(combined_text) > max_chars:
        combined_text = combined_text[:max_chars] + "\n\n[...текст обрезан...]"

    prompt = f"""Ты — научный редактор. На основе предоставленных материалов напиши статью на тему: «{topic}».

Требования к статье:
1. Язык — русский.
2. Стиль — научно-популярный, понятный.
3. Структура: заголовок, краткое summary (2-3 предложения), введение (зачем тема важна), основная часть (2-4 раздела), практическая значимость, выводы, список источников.
4. Объём — примерно 800–1500 слов.
5. Обязательно опирайся ТОЛЬКО на факты из предоставленных материалов. Если данных не хватает — прямо напиши об этом в тексте, не выдумывай.
6. В конце обязательно укажи список источников, если они упоминаются в материалах.

Вот исходные материалы:
---
{combined_text}
---

Напиши статью."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=8000,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Ошибка при обращении к ИИ: {e}"
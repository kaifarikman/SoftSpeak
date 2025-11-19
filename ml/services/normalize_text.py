"""Нормализация текста для обработки."""
import re
from typing import Union


def normalize_text(text: Union[str, None]) -> str:
    """Нормализует текст: приводит к нижнему регистру, убирает лишние пробелы."""
    if text is None or text == "":
        return ""

    # # 1. Приводим к нижнему регистру
    text = str(text).lower()

    # # 2. Убираем звёздочки и лишние пробелы вокруг них
    text = re.sub(r'\s*\*\s*', '; ', text)
    text = re.sub(r';;', ';', text)

    # # 4. Убираем множественные пробелы и лишние переносы
    text = re.sub(r'\s+', ' ', text)

    # # 6. Убираем точку в самом конце, если она одна
    text = text.rstrip(' .')

    return text.strip()


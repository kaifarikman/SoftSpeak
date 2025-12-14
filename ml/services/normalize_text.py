import re
from typing import Union


def normalize_text(text: Union[str, None]) -> str:
    if text is None or text == "":
        return ""
    text = str(text).lower()
    text = re.sub("\\s*\\*\\s*", "; ", text)
    text = re.sub(";;", ";", text)
    text = re.sub("\\s+", " ", text)
    text = text.rstrip(" .")
    return text.strip()

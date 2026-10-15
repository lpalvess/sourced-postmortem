"""Utilitários de texto."""
import re
import unicodedata


def strip_markup(text: str) -> str:
    return text.replace("**", "").replace("__", "").replace("`", "")


def norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return strip_markup(plain).lower().strip()


def word_in(term: str, text: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) is not None


def starts_word(term: str, text: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(term), text) is not None


def short(text: str, limit: int = 60) -> str:
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text

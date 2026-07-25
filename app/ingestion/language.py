"""
Language detection utilities.
"""

from enum import StrEnum
from pathlib import Path


class Language(StrEnum):
    """
    Enum for all supported languages.
    """

    ENGLISH = "en"  # English
    JAPANESE = "ja"  # Japanese
    MIXED = "mixed"  # English/Japanese mix
    UNKNOWN = "unknown"  # Unknown language (failed to detect)


def detect_language(text: str) -> Language:
    """
    Detects the language of the given text. Not all languages/combinations are supported.

    See definition of `Language` for details.
    """
    if text == "" or text.isspace():
        return Language.UNKNOWN

    # This is a naiive implementation that only supports English and Japanese.
    # Detects Japanese and CJK characters by checking the character code is in one of these rangers:
    # - Hiragana U+3040–U+309F
    # - Katakana U+30A0–U+30FF
    # - CJK Unified Ideographs U+4E00–U+9FFF
    # There are a bunch of CJK extension ranges as well but skip them for now.

    # Unicode ranges for Japanese characters. Upper bound is exclusive so need to add 1 to allow for c in UR...
    ur_hiragana = range(0x3040, 0x309F + 1)
    ur_katakana = range(0x30A0, 0x30FF + 1)
    ur_cjk_unified_ideographs = range(0x4E00, 0x9FFF + 1)

    ratio_significance = 0.08

    text_stripped = text.strip()
    total_char_count = max(len(text_stripped), 1)

    english_char_count = 0
    cjk_char_count = 0
    for c in text_stripped:
        charcode = ord(c)

        if _check_char_in_range(charcode, ur_hiragana) or _check_char_in_range(charcode, ur_katakana) or _check_char_in_range(charcode, ur_cjk_unified_ideographs):
            cjk_char_count += 1
        elif c.isascii() and c.isalpha():
            english_char_count += 1

    cjk_ratio = cjk_char_count / total_char_count
    english_ratio = english_char_count / total_char_count

    if cjk_ratio >= ratio_significance and english_ratio >= ratio_significance:
        return Language.MIXED

    if cjk_ratio >= ratio_significance:
        return Language.JAPANESE

    if english_ratio >= ratio_significance:
        return Language.ENGLISH

    return Language.UNKNOWN


def detect_language_from_path(path: str | Path) -> Language | None:
    """
    Detects the language of the given file path.

    Specific to the data/manuals directory.
    """

    path_sections = Path(path).parts

    for i, part in enumerate[str](path_sections):
        if part == "data" and i + 2 < len(path_sections) and path_sections[i + 1] == "manuals":
            # Can't just do `part in Language` because UNKNOWN and MIXED are not valid language names.

            language_folder_name: str = path_sections[i + 2].lower()

            if language_folder_name == "en":
                return Language.ENGLISH

            if language_folder_name == "ja":
                return Language.JAPANESE

    return None


def _check_char_in_range(charcode: int, range: range) -> bool:
    """
    Returns True if the given character code is in the given range.
    """

    return charcode in range

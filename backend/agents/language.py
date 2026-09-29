"""Language detection for English / Urdu / Roman Urdu / Mixed."""

from __future__ import annotations

import re
import time

from models.schemas import Language

ARABIC_URDU_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")

# Common English function words — signal of English prose
ENGLISH_STOPWORDS = {
    "the",
    "and",
    "for",
    "you",
    "your",
    "with",
    "this",
    "that",
    "from",
    "have",
    "will",
    "can",
    "are",
    "is",
    "to",
    "of",
    "in",
    "on",
    "please",
    "open",
    "using",
    "available",
    "based",
    "here",
    "sure",
    "according",
}

# Allowed Latin tokens inside Urdu replies (brands / acronyms)
URDU_LATIN_ALLOW = {
    "jazzcash",
    "raast",
    "lesco",
    "ssgc",
    "sngpl",
    "ptcl",
    "iban",
    "cnic",
    "mpin",
    "otp",
    "qr",
    "rs",
    "pkr",
    "hbl",
    "ubl",
    "mcb",
    "kyc",
    "app",
    "pin",
    "sms",
    "sim",
    "gb",
    "mb",
    "ready",
    "cash",
    "loan",
}

ROMAN_URDU_MARKERS = {
    "hai",
    "hain",
    "kya",
    "kyun",
    "kyunke",
    "mujhe",
    "mera",
    "meri",
    "mere",
    "aap",
    "apko",
    "kaise",
    "kahan",
    "karna",
    "karo",
    "kar",
    "bhej",
    "bhejo",
    "paisa",
    "rupay",
    "bilkul",
    "nahi",
    "han",
    "haan",
    "theek",
    "wala",
    "wali",
    "kitni",
    "kitna",
    "chahiye",
    "chahta",
    "chahti",
    "sakta",
    "sakti",
    "hun",
    "houn",
    "gai",
    "gaya",
    "gyi",
    "mein",
    "yeh",
    "woh",
    "krna",
    "kryn",
    "karein",
    "dijye",
    "batao",
    "bataen",
    "zarurat",
}


def urdu_script_ratio(text: str) -> float:
    urdu = len(ARABIC_URDU_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    total = urdu + latin
    if total == 0:
        return 0.0
    return urdu / total


def has_urdu_script(text: str) -> bool:
    return bool(ARABIC_URDU_RE.search(text))


def _latin_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-']*", text)]


def response_matches_language(text: str, language: Language, *, strict: bool = False) -> bool:
    """Check that the reply matches the required language.

    When ``strict=True`` (UI language lock), Urdu must stay in Arabic script
    for the whole reply — used to stop mid-conversation English drift.
    """
    if not text or not text.strip():
        return False

    cleaned = text.strip()
    if cleaned.startswith("{") and '"response"' in cleaned:
        return False

    ratio = urdu_script_ratio(text)
    words = _latin_words(text)
    non_allow = [w for w in words if w not in URDU_LATIN_ALLOW and len(w) > 2]
    eng_stops = sum(1 for w in words if w in ENGLISH_STOPWORDS)

    if language == Language.URDU:
        min_ratio = 0.65 if strict else 0.55
        max_eng = 2 if strict else 3
        max_non_allow = 6 if strict else 10
        if ratio < min_ratio:
            return False
        if eng_stops >= max_eng:
            return False
        if len(non_allow) >= max_non_allow and ratio < 0.8:
            return False
        lower = text.lower()
        english_leaks = (
            "your next",
            "based on",
            "i can help",
            "you have",
            "you can",
            "according to",
            "here is",
            "here's",
        )
        if any(p in lower for p in english_leaks) and ratio < 0.8:
            return False
        return True

    if language == Language.ENGLISH:
        if ratio >= (0.05 if strict else 0.12):
            return False
        if has_urdu_script(text) and len(ARABIC_URDU_RE.findall(text)) >= (3 if strict else 8):
            return False
        return True

    if language == Language.ROMAN_URDU:
        if ratio >= 0.35:
            return True
        hits = sum(1 for w in words if w in ROMAN_URDU_MARKERS)
        if eng_stops >= 5 and hits < 2:
            return False
        return hits >= 1 or len(words) <= 6

    return True


def detect_language(text: str) -> tuple[Language, float]:
    start = time.perf_counter()
    raw = text.strip()
    if not raw:
        return Language.ENGLISH, (time.perf_counter() - start) * 1000

    ratio = urdu_script_ratio(raw)
    has_script = has_urdu_script(raw)
    tokens = re.findall(r"[A-Za-z']+", raw.lower())
    roman_hits = sum(1 for t in tokens if t in ROMAN_URDU_MARKERS)
    englishish = max(0, len(tokens) - roman_hits)

    if has_script:
        if ratio >= 0.35 or len(ARABIC_URDU_RE.findall(raw)) >= 3:
            lang = Language.URDU
        else:
            lang = Language.MIXED
    elif roman_hits >= 1 and (roman_hits >= 2 or roman_hits >= englishish * 0.35):
        if roman_hits >= 2:
            lang = Language.ROMAN_URDU
        else:
            lang = Language.MIXED
    else:
        lang = Language.ENGLISH

    return lang, (time.perf_counter() - start) * 1000

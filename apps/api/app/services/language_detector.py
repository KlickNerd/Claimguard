from langdetect import DetectorFactory, detect_langs

# Deterministic results across runs (langdetect is stochastic by default).
DetectorFactory.seed = 42


def detect_primary_language(text: str) -> str:
    """Return the dominant language code (e.g. ``"de"``) or ``"unknown"``."""
    try:
        candidates = detect_langs(text)
    except Exception:
        return "unknown"
    if not candidates:
        return "unknown"
    return candidates[0].lang


def is_german(text: str, min_confidence: float = 0.6) -> bool:
    """True if the text is primarily German with sufficient confidence.

    We check the single top candidate rather than summing probabilities because
    mixed DE/EN input is explicitly out of scope for the MVP (PROJ-11 rule).
    """
    try:
        candidates = detect_langs(text)
    except Exception:
        return False
    for candidate in candidates:
        if candidate.lang == "de":
            return candidate.prob >= min_confidence
    return False

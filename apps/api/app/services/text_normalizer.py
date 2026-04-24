import bleach
import ftfy

# Whitespace collapse done at the very end so position indices stay meaningful.


def normalize_text(raw: str) -> str:
    """Clean user input before we hand it to the LLM.

    - Fix mojibake (ftfy) so "fÃ¼r" becomes "für".
    - Strip any HTML so paste-from-Word or URL-extraction residues don't bleed in.
    - Replace smart / typographic quotes with ASCII equivalents so subsequent
      ``str.find`` on the LLM's claim-text is robust against typography drift.
    - Collapse Windows-style line endings; leave single newlines intact because
      paragraph structure helps the detector.
    """
    text = ftfy.fix_text(raw)
    text = bleach.clean(text, tags=[], strip=True)
    text = (
        text.replace(" ", " ")
        .replace("‘", "'")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("–", "-")
        .replace("—", "-")
    )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()

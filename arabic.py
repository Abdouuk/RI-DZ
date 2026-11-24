import arabic_reshaper
from bidi.algorithm import get_display


def shape(text):
    """يحوّل النص العربي إلى حروف متصلة وباتجاه صحيح، ويترك النص غير العربي كما هو."""
    if not text:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text

"""后台配置的多语言。简体中文仍写在原字段里，其他语言写在 texts。"""
import json

from Apps.views.Otome.i18n import canonical, current_lang

SOURCE = "zh-Hans"

GAME_FIELDS = ("title", "subtitle", "summary")
GAME_LIMITS = {"title": 100, "subtitle": 200}
CHARACTER_FIELDS = ("name", "title", "intro")
CHARACTER_LIMITS = {"name": 50, "title": 100}
IMAGE_FIELDS = ("label",)
IMAGE_LIMITS = {"label": 50}
NODE_FIELDS = ("speaker_name", "content", "insert_title", "ending_title")
NODE_LIMITS = {"speaker_name": 50, "insert_title": 100, "ending_title": 100}
CHOICE_FIELDS = ("text",)
CHOICE_LIMITS = {"text": 200}
GALLERY_FIELDS = ("title",)
GALLERY_LIMITS = {"title": 100}
ASSET_FIELDS = ("name", "remark")
ASSET_LIMITS = {"name": 100, "remark": 200}
AD_FIELDS = ("title",)
AD_LIMITS = {"title": 100}
CHANNEL_FIELDS = ("name", "remark")
CHANNEL_LIMITS = {"name": 100, "remark": 200}

_NARRATOR = {
    "zh-Hant": "旁白",
    "en": "Narrator",
    "ja": "ナレーション",
    "ko": "내레이션",
    "es": "Narrador",
    "fr": "Narrateur",
    "de": "Erzähler",
    "pt": "Narrador",
    "ru": "Рассказчик",
    "ar": "الراوي",
    "th": "ผู้บรรยาย",
    "vi": "Người dẫn",
    "id": "Narator",
    "it": "Narratore",
    "tr": "Anlatıcı",
    "pl": "Narrator",
    "nl": "Verteller",
    "hi": "कथावाचक",
    "ms": "Pencerita",
    "fil": "Tagapagsalaysay",
    "sv": "Berättare",
}


def clean_texts(raw, fields, limits=None, source=SOURCE):
    if raw in (None, ""):
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as exc:
            raise ValueError("bad json") from exc
    if not isinstance(raw, dict):
        raise ValueError("bad texts")
    allowed = set(fields)
    limits = limits or {}
    source = canonical(source) or SOURCE
    cleaned = {}
    for code, pack in raw.items():
        lang = canonical(str(code))
        if not lang or lang == source or not isinstance(pack, dict):
            continue
        row = {}
        for field in allowed:
            if field not in pack:
                continue
            text = str(pack.get(field) or "").strip()
            limit = limits.get(field)
            if limit:
                text = text[:limit]
            if text:
                row[field] = text
        if row:
            cleaned[lang] = row
    return cleaned


def field_text(obj, field, default=""):
    base = default if obj is None else getattr(obj, field, default)
    base = "" if base is None else str(base)
    if obj is None:
        return base
    source = canonical(getattr(obj, "lang", "") or "") or SOURCE
    lang = current_lang()
    if lang == source:
        return base
    packs = getattr(obj, "texts", None) or {}
    for code in (lang, "en"):
        if code == source:
            continue
        value = (packs.get(code) or {}).get(field)
        if isinstance(value, str) and value.strip():
            return value
    return base


def matches_lang(obj):
    """主语言或已经写了当前语言译文的配置，才算这一语言的内容。"""
    if obj is None:
        return False
    lang = current_lang()
    source = canonical(getattr(obj, "lang", "") or "") or SOURCE
    if source == lang:
        return True
    return bool((getattr(obj, "texts", None) or {}).get(lang))


def prefer_lang(rows):
    matched = [row for row in rows if matches_lang(row)]
    return matched or list(rows)


def narrator():
    lang = current_lang()
    if lang == SOURCE:
        return "旁白"
    return _NARRATOR.get(lang) or _NARRATOR["en"]

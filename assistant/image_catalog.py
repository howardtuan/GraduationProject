"""Local album search for the natural-language visualization module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable

from django.conf import settings


IMAGE_ALIASES: dict[str, list[str]] = {
    "001.jpeg": ["岩石", "海邊", "石頭", "小琉球"],
    "828eaa7a3469666631769e73a736cf18.jpeg": ["車", "汽車", "紅色"],
    "beach.jpg": ["海灘", "沙灘", "海", "旅遊"],
    "bid3.png": ["鳥", "飛鳥", "動物"],
    "boat.jpg": ["船", "小船", "海邊"],
    "cat.jpeg": ["貓", "貓咪", "動物"],
    "dogt.jpeg": ["狗", "狗狗", "草地", "動物"],
    "frog.jpeg": ["青蛙", "蛙", "動物"],
    "gg.png": ["鹹水雞", "食物", "美食", "蔬菜"],
    "gg2.png": ["霸王", "餐車", "鹹水雞", "招牌"],
    "kg.jpg": ["長頸鹿", "雪地", "動物"],
    "map.png": ["地圖", "路線", "位置"],
    "news.png": ["新聞", "雲", "天氣"],
    "p1.jpeg": ["十字路口", "門口", "路口"],
    "p2.jpeg": ["日新路", "時鐘", "街道"],
    "p3.jpeg": ["屈臣氏", "店面", "招牌"],
    "p4.jpeg": ["對面", "數字", "畫面"],
    "picA.png": ["夕陽", "湖", "風景"],
    "picB.png": ["水域", "湖泊", "船"],
    "poto.png": ["照片", "彩色", "物件"],
    "ttt.jpg": ["森林", "樹", "自然"],
    "花瓶岩.jpeg": ["花瓶岩", "小琉球", "珊瑚礁", "景點"],
    "龍蝦洞.jpeg": ["龍蝦洞", "小琉球", "海蝕溝", "洞穴", "景點"],
}


@dataclass(frozen=True)
class ImageItem:
    """Searchable metadata for one image in the local static album."""

    filename: str
    url: str
    caption: str
    keywords: tuple[str, ...]


def _load_caption_map() -> dict[str, str]:
    """Load generated captions from the legacy JSON file if it exists."""
    caption_file = settings.BASE_DIR / "ImageCaption.json"
    if not caption_file.exists():
        return {}
    try:
        return json.loads(caption_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _normalize_text(text: str) -> str:
    """Normalize text for simple multilingual keyword matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    """Create coarse tokens for English words and Chinese character matching."""
    normalized = _normalize_text(text)
    words = set(re.findall(r"[a-z0-9]+", normalized))
    chinese_chars = set(re.findall(r"[\u4e00-\u9fff]", normalized))
    return words | chinese_chars


def get_catalog() -> list[ImageItem]:
    """Return all images under `static/images` with captions and aliases."""
    image_dir = settings.BASE_DIR / "static" / "images"
    captions = _load_caption_map()
    items: list[ImageItem] = []
    if not image_dir.exists():
        return items

    for path in sorted(image_dir.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            continue
        caption = captions.get(f"./static/images/{path.name}", "")
        stem_words = [path.stem, path.suffix.lstrip(".")]
        aliases = IMAGE_ALIASES.get(path.name, [])
        keywords = tuple(dict.fromkeys(stem_words + aliases))
        items.append(
            ImageItem(
                filename=path.name,
                url=f"{settings.STATIC_URL}images/{path.name}",
                caption=caption,
                keywords=keywords,
            )
        )
    return items


def _score(query: str, item: ImageItem) -> float:
    """Score one image using exact aliases, filename hints, and caption overlap."""
    normalized_query = _normalize_text(query)
    searchable = _normalize_text(" ".join([item.filename, item.caption, *item.keywords]))

    score = 0.0
    for keyword in item.keywords:
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword and normalized_keyword in normalized_query:
            score += 12.0
        if normalized_keyword and normalized_keyword in searchable and normalized_keyword in normalized_query:
            score += 4.0

    query_tokens = _tokens(normalized_query)
    item_tokens = _tokens(searchable)
    if query_tokens and item_tokens:
        score += len(query_tokens & item_tokens) / max(len(query_tokens), 1) * 6.0

    # Fallback for short Chinese phrases that do not tokenize as words.
    common_chars = set(normalized_query) & set(searchable)
    score += min(len(common_chars), 8) * 0.2
    return score


def search_images(query: str, limit: int = 3) -> list[dict[str, str | float | list[str]]]:
    """Search the local album and return the best visual matches."""
    if not query.strip():
        return []
    ranked = sorted(
        ((item, _score(query, item)) for item in get_catalog()),
        key=lambda pair: pair[1],
        reverse=True,
    )
    results = []
    for item, score in ranked[:limit]:
        if score <= 0:
            continue
        results.append(
            {
                "filename": item.filename,
                "url": item.url,
                "caption": item.caption,
                "keywords": list(item.keywords),
                "score": round(score, 3),
            }
        )
    return results


def resolve_keywords_to_images(keywords: Iterable[str]) -> list[dict[str, str | float | list[str]]]:
    """Resolve slide `PIC` keywords to static image URLs when possible."""
    resolved: list[dict[str, str | float | list[str]]] = []
    seen_urls: set[str] = set()
    for keyword in keywords:
        for image in search_images(keyword, limit=1):
            url = str(image["url"])
            if url not in seen_urls:
                resolved.append(image)
                seen_urls.add(url)
    return resolved

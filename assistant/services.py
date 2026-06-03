"""Business logic for Talk2Draw's three major modules.

The service layer keeps Django views thin and gives every AI feature a safe
fallback so the app can still be tested when Ollama is not available.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from django.conf import settings

from .image_catalog import resolve_keywords_to_images, search_images
from .prompts import INTENT_PROMPT, SLIDE_PROMPT, SUMMARY_PROMPT


INTENT_VALUES = {"AI生圖", "相簿取圖", "爬蟲模式", "簡報模式", "圖表模式", "None"}
EXIT_PRESENTATION_WORDS = ("離開簡報模式", "結束簡報模式", "退出簡報模式")
NEXT_SLIDE_WORDS = ("下一頁", "下一張", "換頁", "新投影片")


class AIUnavailable(RuntimeError):
    """Raised when a configured AI-backed feature cannot be executed."""


@dataclass
class AITextClient:
    """Small wrapper around Ollama's local chat API."""

    base_url: str
    model: str
    timeout: int = 30

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """Return model text from a local Ollama chat model."""
        if not self.base_url or not self.model:
            raise AIUnavailable("OLLAMA_BASE_URL and OLLAMA_CHAT_MODEL must be configured.")
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - covered by dependency install.
            raise AIUnavailable("The requests package is not installed.") from exc

        endpoint = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise AIUnavailable(f"Ollama request failed: {exc}") from exc

        text = data.get("message", {}).get("content", "")
        if not text:
            raise AIUnavailable("Ollama returned an empty response.")
        return text.strip()


def build_ai_text_client() -> AITextClient:
    """Build the configured local AI text client."""
    if settings.AI_PROVIDER != "ollama":
        raise AIUnavailable(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")
    return AITextClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_CHAT_MODEL,
        timeout=settings.OLLAMA_TIMEOUT,
    )


def _ai_client() -> AITextClient:
    """Build the configured AI text client."""
    return build_ai_text_client()


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    """Check if any trigger word exists in text."""
    return any(word in text for word in words)


def rule_based_intent(text: str) -> str:
    """Classify intent without external APIs for offline testing."""
    normalized = text.strip().lower()
    if not normalized:
        return "None"
    if any(word in normalized for word in ["ai生圖", "產生圖", "生成圖片", "畫一張", "dall", "dalle"]):
        return "AI生圖"
    if any(word in normalized for word in ["相簿", "本機照片", "我的照片", "我的圖片", "相片庫", "曾經看"]):
        return "相簿取圖"
    if any(word in normalized for word in ["查", "搜尋", "新聞", "網路", "資料", "即時", "報導", "介紹", "是什麼", "找圖", "圖片", "照片", "給我看"]):
        return "爬蟲模式"
    if any(word in normalized for word in ["簡報", "投影片", "ppt", "下一頁", "口說簡報"]):
        return "簡報模式"
    if any(word in normalized for word in ["圖表", "長條圖", "折線圖", "圓餅圖", "銷售額", "營收"]):
        return "圖表模式"
    return "None"


def classify_intent(text: str) -> dict[str, str]:
    """Classify user speech into one of the supported modes."""
    fallback = rule_based_intent(text)
    if fallback != "None":
        return {"intent": fallback, "source": "rules"}
    try:
        ai_result = _ai_client().complete(INTENT_PROMPT, text, temperature=0)
        cleaned = ai_result.strip().splitlines()[0].strip(" `。")
        if cleaned in INTENT_VALUES:
            return {"intent": cleaned, "source": "ollama"}
    except Exception:
        pass
    return {"intent": fallback, "source": "rules"}


def normalize_transcript_text(transcript) -> str:
    """Flatten UI/API transcript formats into readable plain text."""
    if transcript is None:
        return ""
    if isinstance(transcript, str):
        return transcript.strip()
    if isinstance(transcript, list):
        lines = [normalize_transcript_text(item) for item in transcript]
        return "\n".join(line for line in lines if line)
    if isinstance(transcript, dict):
        role = str(transcript.get("role") or transcript.get("speaker") or "").strip()
        content = (
            transcript.get("content")
            or transcript.get("text")
            or transcript.get("message")
            or transcript.get("input")
        )
        if content is None:
            values = [
                normalize_transcript_text(value)
                for key, value in transcript.items()
                if key not in {"role", "speaker"}
            ]
            content_text = " ".join(value for value in values if value)
        else:
            content_text = normalize_transcript_text(content)
        return f"{role}: {content_text}" if role and content_text else content_text
    return str(transcript).strip()


def fallback_summary(transcript) -> str:
    """Create a deterministic summary when Ollama is unavailable."""
    transcript = normalize_transcript_text(transcript)
    compact = re.sub(r"\s+", " ", transcript).strip()
    if not compact:
        compact = "未提供逐字稿"
    sentences = [item.strip() for item in re.split(r"[。！？!?\n]+", transcript) if item.strip()]
    bullets = sentences[:5] or [compact[:80]]
    outline = "\n".join(f"{index + 1}. {sentence[:45]}" for index, sentence in enumerate(bullets[:3]))
    points = "\n".join(f"- {sentence[:90]}" for sentence in bullets)
    return f"主題：\n{bullets[0][:40] if bullets else '未提及'}\n大綱：\n{outline}\n重點整理：\n{points}\n待辦事項：\n- 未提及"


def summarize_dialogue(transcript) -> dict[str, str]:
    """Summarize a dialogue transcript into a report-friendly structure."""
    transcript_text = normalize_transcript_text(transcript)
    try:
        text = _ai_client().complete(SUMMARY_PROMPT, transcript_text, temperature=0.1)
        return {"summary": text, "source": "ollama"}
    except Exception:
        return {"summary": fallback_summary(transcript_text), "source": "rules"}


def blank_slide() -> dict[str, list[str] | str]:
    """Return the canonical empty slide shape."""
    return {"Title": "", "LittleTitle": [], "Content": [], "PIC": []}


def _extract_json_object(text: str) -> dict | str | None:
    """Parse model JSON while tolerating accidental surrounding text."""
    stripped = text.strip()
    if stripped == '"None"' or stripped == "None":
        return "None"
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def normalize_slide(raw_slide: dict | None) -> dict[str, list[str] | str]:
    """Validate and normalize a model-generated slide object."""
    if not isinstance(raw_slide, dict):
        return blank_slide()
    slide = blank_slide()
    slide["Title"] = str(raw_slide.get("Title", "") or "").strip()
    for key in ("LittleTitle", "Content", "PIC"):
        value = raw_slide.get(key, [])
        if isinstance(value, str):
            value = [value] if value.strip() else []
        if not isinstance(value, list):
            value = []
        slide[key] = [str(item).strip() for item in value if str(item).strip()]
    return slide


def fallback_slide(text: str, current_slide: dict | None = None) -> dict[str, list[str] | str]:
    """Create a simple slide locally when the AI service is unavailable."""
    if _contains_any(text, NEXT_SLIDE_WORDS):
        return blank_slide()

    slide = normalize_slide(current_slide)
    cleaned = re.sub(r"\s+", " ", text).strip(" ，。")
    if not cleaned:
        return slide

    if not slide["Title"]:
        title_match = None
        for pattern in (
            r"(?:主題|題目)(?:是|為|就是|：|:)\s*([^，。,.]+)",
            r"今天(?:我)?要介紹(?:的主題)?(?:是|為|就是|：|:)?\s*([^，。,.]+)",
            r"介紹(?:一下)?\s*([^，。,.]+)",
        ):
            title_match = re.search(pattern, cleaned)
            if title_match:
                break
        slide["Title"] = title_match.group(1).strip() if title_match else cleaned[:24]

    ordered_topics = re.findall(r"(?:第一|第二|第三|第四|第五|一、|二、|三、|四、|五、)(?:是|則是)?([^，。,.]+)", cleaned)
    for topic in ordered_topics:
        topic = topic.strip()
        if topic and topic not in slide["LittleTitle"]:
            slide["LittleTitle"].append(topic)

    if not ordered_topics and cleaned not in slide["Content"]:
        slide["Content"].append(cleaned[:120])

    image_hits = search_images(cleaned, limit=2)
    for image in image_hits:
        keyword = _best_image_keyword(image, cleaned)
        if keyword not in slide["PIC"]:
            slide["PIC"].append(keyword)
    return slide


def _best_image_keyword(image: dict, source_text: str) -> str:
    """Pick a human-readable keyword from an image search result."""
    keywords = [str(item) for item in image.get("keywords", [])]
    for keyword in keywords:
        if keyword and keyword in source_text:
            return keyword
    for keyword in keywords:
        if keyword and not keyword.isascii() and keyword not in {"jpeg", "jpg", "png"}:
            return keyword
    return Path(str(image.get("filename", ""))).stem


def build_presentation_slide(text: str, current_slide: dict | None = None) -> dict:
    """Generate or update one presentation slide from spoken text."""
    if _contains_any(text, EXIT_PRESENTATION_WORDS):
        return {"response": "None", "slide": blank_slide(), "source": "rules", "should_exit": True}

    current = normalize_slide(current_slide)
    prompt_input = json.dumps(
        {"current_slide": current, "utterance": text},
        ensure_ascii=False,
    )
    try:
        ai_text = _ai_client().complete(SLIDE_PROMPT, prompt_input, temperature=0.2)
        parsed = _extract_json_object(ai_text)
        if parsed == "None":
            slide = blank_slide()
            return {"response": "None", "slide": slide, "source": "ollama", "should_exit": True}
        slide = normalize_slide(parsed if isinstance(parsed, dict) else None)
        source = "ollama"
    except Exception:
        slide = fallback_slide(text, current)
        source = "rules"

    images = resolve_keywords_to_images(slide["PIC"])
    return {
        "response": json.dumps(slide, ensure_ascii=False),
        "slide": slide,
        "images": images,
        "source": source,
        "should_exit": False,
    }


def semantic_image_search(text: str) -> dict:
    """Return local album images that best visualize the current sentence."""
    images = search_images(text, limit=3)
    response = f"*{images[0]['url']}" if images else ""
    return {"response": response, "images": images, "source": "local_catalog"}


def _request_headers() -> dict[str, str]:
    """Return headers accepted by lightweight search and preview pages."""
    return {
        "User-Agent": "Talk2Draw/1.0 (+local research assistant)",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
    }


def search_web(query: str) -> dict:
    """Fetch lightweight web search results for the smart retrieval module."""
    if not query.strip():
        return {"results": [], "source": "duckduckgo", "error": "empty query"}

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {"results": [], "source": "duckduckgo", "error": "requests/beautifulsoup4 not installed"}

    try:
        response = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers=_request_headers(),
            timeout=settings.TALK2DRAW_SEARCH_TIMEOUT,
        )
        response.raise_for_status()
    except Exception as exc:
        return {"results": [], "source": "duckduckgo", "error": str(exc)}

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for result in soup.select(".result")[:5]:
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if not link:
            continue
        href = link.get("href", "")
        results.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": _clean_duckduckgo_url(href),
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
            }
        )
    images = find_web_images(query, results=results, limit=4)
    return {"results": results, "images": images, "source": "duckduckgo", "error": ""}


def find_web_images(query: str, *, results: list[dict] | None = None, limit: int = 4) -> list[dict[str, str]]:
    """Extract relevant preview images from top web results without using the local album."""
    if not query.strip() or limit <= 0:
        return []

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    images = _search_bing_images(query, limit=limit)
    if len(images) >= limit:
        return images[:limit]

    candidates = results
    if candidates is None:
        candidates = search_web(query).get("results", [])

    seen_urls: set[str] = set()
    for image in images:
        seen_urls.add(image["url"])

    page_timeout = min(settings.TALK2DRAW_SEARCH_TIMEOUT, 4)
    for item in candidates[:6]:
        page_url = str(item.get("url") or "")
        if not page_url.startswith(("http://", "https://")):
            continue
        try:
            response = requests.get(page_url, headers=_request_headers(), timeout=page_timeout)
            response.raise_for_status()
        except Exception:
            continue

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        image_url = _extract_preview_image(soup, page_url)
        if not image_url or image_url in seen_urls:
            continue
        title = str(item.get("title") or "")
        if not _is_relevant_image_candidate(query, title, page_url):
            continue
        seen_urls.add(image_url)
        images.append(
            {
                "url": image_url,
                "title": title,
                "source_url": page_url,
                "source_title": str(item.get("title") or urlparse(page_url).netloc),
            }
        )
        if len(images) >= limit:
            break
    return images


def _search_bing_images(query: str, limit: int = 4) -> list[dict[str, str]]:
    """Read Bing image search metadata and keep only text-relevant image hits."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    try:
        response = requests.get(
            "https://www.bing.com/images/search",
            params={"q": query, "form": "HDRSC2", "first": "1"},
            headers=_request_headers(),
            timeout=settings.TALK2DRAW_SEARCH_TIMEOUT,
        )
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    images: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for link in soup.select("a.iusc")[:20]:
        metadata = link.get("m", "")
        if not metadata:
            continue
        try:
            data = json.loads(metadata)
        except json.JSONDecodeError:
            continue

        title = str(data.get("t") or "")
        source_url = str(data.get("purl") or "")
        if not _is_relevant_image_candidate(query, title, source_url):
            continue

        image_url = _normalize_image_url(str(data.get("murl") or data.get("turl") or ""), source_url or response.url)
        if not image_url or image_url in seen_urls:
            continue
        seen_urls.add(image_url)
        images.append(
            {
                "url": image_url,
                "title": title,
                "source_url": source_url,
                "source_title": title or urlparse(source_url).netloc,
            }
        )
        if len(images) >= limit:
            break
    return images


def _query_terms(query: str) -> list[str]:
    """Extract useful matching terms while dropping generic assistant words."""
    stop_words = {
        "ai",
        "圖片",
        "照片",
        "參考",
        "生成",
        "生成圖片",
        "生圖",
        "畫圖",
        "幫我",
        "我想看",
        "給我看",
        "查詢",
        "搜尋",
        "相關",
    }
    punctuation_pattern = r"[\s:\uFF1A\uFF0C,。.!！\uFF1F?「」『』()\uFF08\uFF09\[\]{}]+"
    normalized = re.sub(punctuation_pattern, " ", query.lower())
    chunks = []
    for raw_chunk in normalized.split():
        raw_chunk = raw_chunk.strip()
        for prefix in ("請幫我查", "請幫我找", "幫我查", "幫我找", "請幫我", "我想看", "給我看", "幫我", "查詢", "搜尋", "找"):
            if raw_chunk.startswith(prefix):
                raw_chunk = raw_chunk[len(prefix) :]
        for suffix in ("圖片", "照片", "圖像", "圖", "參考", "資料", "資訊"):
            if raw_chunk.endswith(suffix):
                raw_chunk = raw_chunk[: -len(suffix)]
        parts = re.split(r"[的在與和及上]+", raw_chunk)
        chunks.extend(part for part in parts if part)

    terms: list[str] = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if len(cleaned) < 2 or cleaned in stop_words:
            continue
        if cleaned not in terms:
            terms.append(cleaned)
    return terms[:8]


def _is_relevant_image_candidate(query: str, title: str, source_url: str = "") -> bool:
    """Reject image hits that look like generic site logos or unrelated covers."""
    terms = _query_terms(query)
    if not terms:
        return True
    haystack = f"{title} {source_url}".lower()
    return any(term in haystack for term in terms)


def _extract_preview_image(soup, page_url: str) -> str:
    """Pick the strongest image URL from a result page."""
    meta_selectors = [
        ('meta[property="og:image"]', "content"),
        ('meta[property="og:image:secure_url"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[name="twitter:image:src"]', "content"),
    ]
    for selector, attr in meta_selectors:
        node = soup.select_one(selector)
        image_url = _normalize_image_url(node.get(attr, "") if node else "", page_url)
        if image_url:
            return image_url

    for img in soup.find_all("img"):
        raw_url = img.get("src") or img.get("data-src") or img.get("data-original")
        image_url = _normalize_image_url(raw_url or "", page_url)
        if image_url:
            return image_url
    return ""


def _normalize_image_url(raw_url: str, page_url: str) -> str:
    """Resolve and filter candidate image URLs."""
    raw_url = raw_url.strip()
    if not raw_url or raw_url.startswith(("data:", "blob:")):
        return ""
    image_url = urljoin(page_url, raw_url)
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    lowered = image_url.lower()
    if any(token in lowered for token in ("favicon", "sprite", "blank", "pixel", "logo.svg")):
        return ""
    if lowered.endswith(".svg"):
        return ""
    return image_url


def _clean_duckduckgo_url(url: str) -> str:
    """Resolve relative DuckDuckGo redirect URLs into usable links."""
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    if "uddg" in query_params and query_params["uddg"]:
        return unquote(query_params["uddg"][0])
    if parsed.scheme:
        return url
    return urljoin("https://duckduckgo.com", url)


def generate_image(prompt: str) -> dict:
    """Return web reference images for drawing prompts without using album fallbacks."""
    if not prompt.strip():
        return {"url": "", "source": "none", "message": "請先輸入要生成的圖片描述。"}
    search_data = search_web(f"{prompt} 圖片 參考")
    images = search_data.get("images", [])
    return {
        "url": images[0]["url"] if images else "",
        "images": images,
        "results": search_data.get("results", []),
        "source": "web_reference",
        "message": "Ollama 目前是地端文字模型；我不會再硬套本機相簿，已改用網路查詢到的相關圖片作為畫圖參考。",
    }


def _number_value(raw_number: str, unit: str) -> float:
    """Convert numeric strings with common Chinese units into real values."""
    value = float(raw_number)
    multiplier = {"千": 1_000, "萬": 10_000, "億": 100_000_000}.get(unit, 1)
    return value * multiplier


def extract_chart_data(text: str) -> dict:
    """Extract simple label/value pairs from spoken numeric descriptions."""
    pattern = re.compile(
        r"([\u4e00-\u9fffA-Za-z0-9]{1,12}?)(?:的)?(?:銷售額|營收|收入|數量|金額)?(?:為|是|有|:|：)?\s*([0-9]+(?:\.[0-9]+)?)(千|萬|億|%)?"
    )
    labels: list[str] = []
    values: list[float] = []
    units: list[str] = []
    for label, number, unit in pattern.findall(text):
        cleaned_label = label.strip("，,。 .")
        if not cleaned_label:
            continue
        labels.append(cleaned_label[-8:])
        values.append(_number_value(number, unit))
        units.append(unit or "")

    if len(values) < 2:
        return {"labels": [], "values": [], "unit": "", "source": "rules"}
    common_unit = next((unit for unit in units if unit), "")
    return {"labels": labels[:8], "values": values[:8], "unit": common_unit, "source": "rules"}

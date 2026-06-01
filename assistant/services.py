"""Business logic for Talk2Draw's three major modules.

The service layer keeps Django views thin and gives every AI feature a safe
fallback so the app can still be tested before production API keys are filled.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import json
import re
import uuid
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from django.conf import settings

from .image_catalog import resolve_keywords_to_images, search_images
from .prompts import INTENT_PROMPT, SLIDE_PROMPT, SUMMARY_PROMPT


INTENT_VALUES = {"AI生圖", "相簿取圖", "爬蟲模式", "簡報模式", "圖表模式", "None"}
EXIT_PRESENTATION_WORDS = ("離開簡報模式", "結束簡報模式", "退出簡報模式")
NEXT_SLIDE_WORDS = ("下一頁", "下一張", "換頁", "新投影片")


class AIUnavailable(RuntimeError):
    """Raised when an OpenAI-backed feature cannot be executed."""


@dataclass
class AITextClient:
    """Small wrapper that supports both modern and older OpenAI SDK styles."""

    api_key: str
    model: str

    def _client(self):
        """Import OpenAI lazily so rule-based tests do not need the package."""
        if not self.api_key:
            raise AIUnavailable("OPENAI_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - covered by dependency install.
            raise AIUnavailable("The openai package is not installed.") from exc
        return OpenAI(api_key=self.api_key)

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """Return model text using Responses API first, then Chat Completions."""
        client = self._client()
        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            text = getattr(response, "output_text", "")
            if text:
                return text.strip()
        except Exception:
            # Some older SDKs or models may not expose Responses API; the
            # fallback keeps deployments flexible without changing app code.
            pass

        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return completion.choices[0].message.content.strip()


def _ai_client() -> AITextClient:
    """Build the configured AI text client."""
    return AITextClient(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_CHAT_MODEL)


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
    if any(word in normalized for word in ["相簿", "照片", "圖片", "給我看", "找圖", "曾經看"]):
        return "相簿取圖"
    if any(word in normalized for word in ["查", "搜尋", "新聞", "網路", "資料", "即時", "報導"]):
        return "爬蟲模式"
    if any(word in normalized for word in ["簡報", "投影片", "ppt", "下一頁", "口說簡報"]):
        return "簡報模式"
    if any(word in normalized for word in ["圖表", "長條圖", "折線圖", "圓餅圖", "銷售額", "營收"]):
        return "圖表模式"
    return "None"


def classify_intent(text: str) -> dict[str, str]:
    """Classify user speech into one of the supported modes."""
    fallback = rule_based_intent(text)
    try:
        ai_result = _ai_client().complete(INTENT_PROMPT, text, temperature=0)
        cleaned = ai_result.strip().splitlines()[0].strip(" `。")
        if cleaned in INTENT_VALUES:
            return {"intent": cleaned, "source": "openai"}
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
    """Create a deterministic summary when OpenAI is unavailable."""
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
        return {"summary": text, "source": "openai"}
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
            return {"response": "None", "slide": slide, "source": "openai", "should_exit": True}
        slide = normalize_slide(parsed if isinstance(parsed, dict) else None)
        source = "openai"
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
            headers={"User-Agent": "Talk2Draw/1.0"},
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
    return {"results": results, "source": "duckduckgo", "error": ""}


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
    """Generate an image with OpenAI or return a useful local fallback."""
    if not prompt.strip():
        return {"url": "", "source": "none", "message": "請先輸入要生成的圖片描述。"}
    if not settings.OPENAI_API_KEY:
        fallback = search_images(prompt, limit=1)
        return {
            "url": fallback[0]["url"] if fallback else "",
            "source": "local_fallback",
            "message": "尚未設定 OPENAI_API_KEY，已改用本機相簿最接近的圖片。",
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        result = client.images.generate(
            model=settings.OPENAI_IMAGE_MODEL,
            prompt=prompt,
            size=settings.OPENAI_IMAGE_SIZE,
        )
        first = result.data[0]
        b64_json = getattr(first, "b64_json", None)
        image_url = getattr(first, "url", None)
        if b64_json:
            generated_dir = settings.MEDIA_ROOT / "generated"
            generated_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4().hex}.png"
            output_path = generated_dir / filename
            output_path.write_bytes(base64.b64decode(b64_json))
            return {"url": f"{settings.MEDIA_URL}generated/{filename}", "source": "openai", "message": ""}
        if image_url:
            return {"url": image_url, "source": "openai", "message": ""}
    except Exception as exc:
        fallback = search_images(prompt, limit=1)
        return {
            "url": fallback[0]["url"] if fallback else "",
            "source": "local_fallback",
            "message": f"AI 生圖暫時失敗，已改用本機圖片。錯誤：{exc}",
        }

    return {"url": "", "source": "openai", "message": "AI 生圖沒有回傳圖片。"}


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

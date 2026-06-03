"""Jarvis-style agent orchestration for Talk2Draw.

This module borrows the useful OpenJarvis ideas without forcing the whole
runtime into the graduation project: a webchat channel, a skill catalog, and an
agent that routes user messages to tools.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import uuid

from django.conf import settings

from .services import (
    blank_slide,
    build_ai_text_client,
    build_presentation_slide,
    classify_intent,
    extract_chart_data,
    generate_image,
    search_web,
    semantic_image_search,
    summarize_dialogue,
)


MAX_SKILL_BYTES = 512 * 1024
SKILL_EXTENSIONS = {".md", ".markdown", ".json", ".toml", ".txt"}


@dataclass
class JarvisAttachment:
    """A downloadable or viewable artifact produced by the agent."""

    name: str
    url: str
    kind: str = "file"
    mime_type: str = "text/plain"


@dataclass
class SkillManifest:
    """Minimal agentskills/OpenJarvis-compatible skill manifest."""

    name: str
    description: str
    source: str = "local"
    version: str = "0.1.0"
    instructions: str = ""
    trigger_phrases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    imported_at: str = ""


BUILTIN_SKILLS: list[SkillManifest] = [
    SkillManifest(
        name="visualize-speech",
        description="Find local album images that match spoken context.",
        source="builtin",
        trigger_phrases=["圖片", "照片", "相簿", "看"],
        tags=["visual", "album"],
    ),
    SkillManifest(
        name="smart-research",
        description="Search the web and return grounded links.",
        source="builtin",
        trigger_phrases=["查", "搜尋", "新聞", "資料"],
        tags=["search", "research"],
    ),
    SkillManifest(
        name="spoken-slides",
        description="Turn speech into a live presentation slide.",
        source="builtin",
        trigger_phrases=["簡報", "投影片", "下一頁"],
        tags=["presentation"],
    ),
    SkillManifest(
        name="meeting-summary",
        description="Summarize transcripts into topics, outline, notes, and action items.",
        source="builtin",
        trigger_phrases=["摘要", "大綱", "會議紀錄", "整理"],
        tags=["summary"],
    ),
    SkillManifest(
        name="chart-builder",
        description="Extract numbers from speech and render chart-ready data.",
        source="builtin",
        trigger_phrases=["圖表", "銷售額", "營收"],
        tags=["chart"],
    ),
    SkillManifest(
        name="artifact-writer",
        description="Create downloadable markdown or JSON files from agent output.",
        source="builtin",
        trigger_phrases=["檔案", "下載", "匯出", "傳給我"],
        tags=["files"],
    ),
]


def _skill_root() -> Path:
    """Return the runtime skill storage directory."""
    root = settings.MEDIA_ROOT / "skills"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _artifact_root() -> Path:
    """Return the runtime artifact storage directory."""
    root = settings.MEDIA_ROOT / "generated"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slugify(value: str) -> str:
    """Create a filesystem-safe skill or artifact slug."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or f"skill-{uuid.uuid4().hex[:8]}"


def _safe_filename(value: str, suffix: str = ".md") -> str:
    """Create a safe filename while preserving a useful readable stem."""
    stem = _slugify(Path(value).stem or "artifact")
    return f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"


def _relative_media_url(path: Path) -> str:
    """Build a URL served by the media download route."""
    relative = path.resolve().relative_to(settings.MEDIA_ROOT.resolve())
    return f"{settings.MEDIA_URL}{relative.as_posix()}"


def _write_artifact(name: str, content: str, mime_type: str = "text/markdown") -> JarvisAttachment:
    """Persist generated content and return it as a chat attachment."""
    suffix = ".md" if "markdown" in mime_type or mime_type == "text/plain" else ".json"
    output_path = _artifact_root() / _safe_filename(name, suffix=suffix)
    output_path.write_text(content, encoding="utf-8")
    return JarvisAttachment(name=output_path.name, url=_relative_media_url(output_path), mime_type=mime_type)


def _load_imported_skills() -> list[SkillManifest]:
    """Read installed skill manifests from disk."""
    skills: list[SkillManifest] = []
    for manifest_path in sorted(_skill_root().glob("*/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            skills.append(SkillManifest(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    return skills


def list_skills() -> list[dict]:
    """Return built-in and imported skills as serializable dictionaries."""
    return [asdict(skill) for skill in [*BUILTIN_SKILLS, *_load_imported_skills()]]


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract a small YAML-like frontmatter block from SKILL.md content."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for raw_line in parts[1].splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        cleaned = value.strip().strip("\"'")
        meta[key.strip()] = cleaned
    return meta, parts[2].strip()


def _coerce_list(value) -> list[str]:
    """Normalize strings or lists into a clean string list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，\n]", value) if item.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _manifest_from_bytes(filename: str, content: bytes) -> SkillManifest:
    """Parse JSON, TOML, or SKILL.md into a safe local manifest."""
    if len(content) > MAX_SKILL_BYTES:
        raise ValueError("Skill file is too large.")
    suffix = Path(filename).suffix.lower()
    if suffix not in SKILL_EXTENSIONS:
        raise ValueError("Only .md, .json, .toml, and .txt skill files are supported.")

    text = content.decode("utf-8", errors="replace").strip()
    imported_at = datetime.now(timezone.utc).isoformat()
    data: dict = {}
    body = text

    if suffix == ".json":
        data = json.loads(text)
    elif suffix == ".toml":
        import tomli

        parsed = tomli.loads(text)
        data = parsed.get("skill", parsed)
    else:
        data, body = _frontmatter(text)

    name = str(data.get("name") or Path(filename).stem).strip()
    first_body_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    description = str(data.get("description") or first_body_line or "Imported skill").strip()
    return SkillManifest(
        name=name,
        description=description,
        source="imported",
        version=str(data.get("version") or "0.1.0"),
        instructions=str(data.get("instructions") or data.get("instruction") or body),
        trigger_phrases=_coerce_list(data.get("trigger_phrases") or data.get("triggers") or data.get("tags")),
        tags=_coerce_list(data.get("tags")),
        imported_at=imported_at,
    )


def import_skill(filename: str, content: bytes) -> dict:
    """Install a declarative skill into the local catalog."""
    manifest = _manifest_from_bytes(filename, content)
    slug = _slugify(manifest.name)
    skill_dir = _skill_root() / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "manifest.json").write_text(json.dumps(asdict(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    source_path = skill_dir / f"source{Path(filename).suffix.lower() or '.txt'}"
    source_path.write_bytes(content)
    return asdict(manifest)


def _matches_skill(message: str, skill: SkillManifest) -> bool:
    """Return True if the message should activate an imported skill."""
    haystack = message.lower()
    candidates = [skill.name, *skill.trigger_phrases, *skill.tags]
    return any(candidate and candidate.lower() in haystack for candidate in candidates)


def _selected_imported_skill(message: str) -> SkillManifest | None:
    """Pick the first imported skill matching the current message."""
    for skill in _load_imported_skills():
        if _matches_skill(message, skill):
            return skill
    return None


def _needs_file(message: str) -> bool:
    """Detect requests for downloadable output."""
    return any(word in message for word in ("檔案", "下載", "匯出", "傳給我", "存成", "產出"))


def _jarvis_reply(message: str, tool_summary: str, skill: SkillManifest | None = None) -> str:
    """Generate a short Jarvis-style reply with Ollama or a deterministic fallback."""
    skill_note = f"\nActive skill: {skill.name} - {skill.description}" if skill else ""
    prompt = (
        "你是 Talk2Draw 裡的 Jarvis-style agent。"
        "用繁體中文，語氣俐落、可靠、稍微有科技感，但不要浮誇。"
        "請說明你已完成什麼，下一步使用者可以怎麼看結果。"
        f"{skill_note}\nTool result:\n{tool_summary}"
    )
    try:
        return build_ai_text_client().complete(prompt, message, temperature=0.3)
    except Exception:
        pass
    prefix = "收到，已為你處理。"
    if skill:
        prefix = f"收到，已套用 `{skill.name}` skill。"
    return f"{prefix}\n{tool_summary}"


def run_jarvis_agent(message: str, *, current_slide: dict | None = None, transcript: str = "") -> dict:
    """Route one user message through Talk2Draw tools and return a chat payload."""
    cleaned = message.strip()
    if not cleaned:
        return {"reply": "我在線上。給我一個任務，我會接手。", "actions": [], "attachments": [], "stage": {"type": "empty"}}

    actions: list[dict] = []
    attachments: list[JarvisAttachment] = []
    stage: dict = {"type": "empty"}
    selected_skill = _selected_imported_skill(cleaned)

    if "列出" in cleaned and ("skill" in cleaned.lower() or "技能" in cleaned):
        skills = list_skills()
        actions.append({"tool": "skill_catalog", "status": "completed", "detail": f"{len(skills)} skills"})
        skill_lines = "\n".join(f"- {skill['name']}: {skill['description']}" for skill in skills)
        attachment = _write_artifact("jarvis-skills.md", f"# Jarvis Skills\n\n{skill_lines}\n")
        attachments.append(attachment)
        return {
            "reply": f"目前可用 skills 共 {len(skills)} 個。我也把清單整理成檔案給你。",
            "actions": actions,
            "attachments": [asdict(item) for item in attachments],
            "stage": {"type": "skills", "skills": skills},
            "mode": "skills",
            "slide": current_slide or blank_slide(),
        }

    summary_requested = any(word in cleaned for word in ("摘要", "大綱", "重點整理", "逐字稿", "會議紀錄"))
    intent = "摘要模式" if summary_requested else classify_intent(cleaned)["intent"]
    if selected_skill and selected_skill.instructions:
        actions.append({"tool": f"skill:{selected_skill.name}", "status": "selected", "detail": selected_skill.description})

    if summary_requested:
        source_text = transcript or cleaned
        result = summarize_dialogue(source_text)
        actions.append({"tool": "meeting_summary", "status": result.get("source", "completed"), "detail": "summary generated"})
        stage = {"type": "summary", "summary": result["summary"]}
        if _needs_file(cleaned):
            attachments.append(_write_artifact("talk2draw-summary.md", result["summary"]))
        tool_summary = result["summary"]
    elif intent == "爬蟲模式":
        result = search_web(cleaned)
        detail = f"{len(result.get('results', []))} results · {len(result.get('images', []))} images"
        actions.append({"tool": "smart_search", "status": "completed", "detail": detail})
        stage = {"type": "search", **result}
        top = result.get("results", [])[:3]
        tool_summary = "已完成即時檢索與相關圖片整理。\n" + "\n".join(f"- {item['title']}" for item in top) if top else "即時檢索沒有找到穩定結果。"
    elif intent == "AI生圖":
        result = generate_image(cleaned)
        detail = f"{len(result.get('images', []))} reference images"
        actions.append({"tool": "image_reference", "status": result.get("source", "completed"), "detail": detail})
        stage = {"type": "generated_image", **result}
        tool_summary = result.get("message") or "已改用網路相關圖片作為畫圖參考。"
    elif intent == "圖表模式":
        result = extract_chart_data(cleaned)
        actions.append({"tool": "chart_builder", "status": "completed", "detail": f"{len(result.get('labels', []))} points"})
        stage = {"type": "chart", **result}
        if _needs_file(cleaned) and result.get("labels"):
            attachments.append(_write_artifact("chart-data.json", json.dumps(result, ensure_ascii=False, indent=2), mime_type="application/json"))
        tool_summary = "圖表資料已建立。" if result.get("labels") else "我還需要至少兩組數值才能建立圖表。"
    elif intent == "簡報模式":
        result = build_presentation_slide(cleaned, current_slide or blank_slide())
        actions.append({"tool": "spoken_slides", "status": result.get("source", "completed"), "detail": "slide updated"})
        stage = {"type": "slide", **result}
        if _needs_file(cleaned):
            slide = result.get("slide", {})
            markdown = f"# {slide.get('Title', '投影片')}\n\n" + "\n".join(f"- {item}" for item in slide.get("Content", []))
            attachments.append(_write_artifact("slide.md", markdown))
        tool_summary = "投影片已更新。"
    elif "整理" in cleaned or _needs_file(cleaned):
        source_text = transcript or cleaned
        result = summarize_dialogue(source_text)
        actions.append({"tool": "meeting_summary", "status": result.get("source", "completed"), "detail": "summary generated"})
        stage = {"type": "summary", "summary": result["summary"]}
        if _needs_file(cleaned):
            attachments.append(_write_artifact("talk2draw-summary.md", result["summary"]))
        tool_summary = result["summary"]
    elif intent == "相簿取圖":
        result = semantic_image_search(cleaned)
        actions.append({"tool": "visualize_speech", "status": "completed", "detail": f"{len(result.get('images', []))} images"})
        stage = {"type": "images", **result}
        tool_summary = "我已從本機相簿挑出視覺素材。" if result.get("images") else "目前沒有找到合適的本機相簿素材。"
    else:
        result = search_web(cleaned)
        detail = f"{len(result.get('results', []))} results · {len(result.get('images', []))} images"
        actions.append({"tool": "assistant_research", "status": "completed", "detail": detail})
        stage = {"type": "search", **result}
        top = result.get("results", [])[:3]
        tool_summary = "我先用全方位助理模式整理網路資訊與相關圖片。\n" + "\n".join(f"- {item['title']}" for item in top) if top else "我沒有找到穩定的網路結果。"

    reply = _jarvis_reply(cleaned, tool_summary, selected_skill)
    return {
        "reply": reply,
        "actions": actions,
        "attachments": [asdict(item) for item in attachments],
        "stage": stage,
        "mode": intent,
        "skill": asdict(selected_skill) if selected_skill else None,
        "slide": stage.get("slide") or current_slide or blank_slide(),
    }

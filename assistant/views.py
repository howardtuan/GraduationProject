"""Django views for the Talk2Draw web interface and JSON APIs."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_safe

from .jarvis_agent import import_skill, list_skills, run_jarvis_agent
from .services import (
    blank_slide,
    build_presentation_slide,
    classify_intent,
    extract_chart_data,
    generate_image,
    normalize_transcript_text,
    search_web,
    semantic_image_search,
    summarize_dialogue,
)


def _json_response(data: dict, status: int = 200) -> JsonResponse:
    """Return JSON with UTF-8 Chinese output preserved."""
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def _body_value(request: HttpRequest, key: str = "inputParam") -> str:
    """Read a string value from JSON POST bodies used by the old Flask UI."""
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    value = payload.get(key, "")
    return str(value).strip()


def _json_payload(request: HttpRequest) -> dict:
    """Parse a JSON request body into a dictionary."""
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


@require_GET
def index(request: HttpRequest):
    """Render the main single-page Talk2Draw workspace."""
    request.session.setdefault("current_slide", blank_slide())
    return render(request, "index.html")


@require_GET
def health(_request: HttpRequest):
    """Simple health endpoint for deployments and smoke tests."""
    return _json_response({"status": "ok"})


@csrf_exempt
@require_POST
def get_sentence_analyze(request: HttpRequest):
    """Classify the current utterance into a Talk2Draw mode."""
    text = _body_value(request)
    if not text:
        return HttpResponseBadRequest("inputParam is required")
    result = classify_intent(text)
    return _json_response({"response": result["intent"], **result})


@csrf_exempt
@require_POST
def get_dialogue_summary(request: HttpRequest):
    """Summarize transcript text for download or review."""
    transcript = _body_value(request)
    result = summarize_dialogue(transcript)
    return _json_response({"response": result["summary"], **result})


@csrf_exempt
@require_POST
def get_ppt(request: HttpRequest):
    """Generate or update a slide from the current spoken sentence."""
    text = _body_value(request)
    current_slide = request.session.get("current_slide", blank_slide())
    result = build_presentation_slide(text, current_slide)
    request.session["current_slide"] = blank_slide() if result["should_exit"] else result["slide"]
    request.session.modified = True
    return _json_response(result)


@csrf_exempt
@require_POST
def semantic_analysis(request: HttpRequest):
    """Search the local album for images matching the utterance."""
    text = _body_value(request)
    if not text:
        return HttpResponseBadRequest("inputParam is required")
    return _json_response(semantic_image_search(text))


@csrf_exempt
@require_POST
def smart_search(request: HttpRequest):
    """Run lightweight web retrieval for the smart search module."""
    query = _body_value(request, "query") or _body_value(request)
    if not query:
        return HttpResponseBadRequest("query is required")
    return _json_response(search_web(query))


@csrf_exempt
@require_POST
def generate_ai_image(request: HttpRequest):
    """Generate an AI image from text or return a local fallback."""
    prompt = _body_value(request, "prompt") or _body_value(request)
    if not prompt:
        return HttpResponseBadRequest("prompt is required")
    return _json_response(generate_image(prompt))


@csrf_exempt
@require_POST
def chart_data(request: HttpRequest):
    """Extract chart-ready labels and values from the utterance."""
    text = _body_value(request, "text") or _body_value(request)
    if not text:
        return HttpResponseBadRequest("text is required")
    return _json_response(extract_chart_data(text))


@csrf_exempt
@require_POST
def jarvis_chat(request: HttpRequest):
    """Chat with the Jarvis-style agent and route actions to project tools."""
    payload = _json_payload(request)
    message = str(payload.get("message", "")).strip()
    if not message:
        return HttpResponseBadRequest("message is required")

    transcript = normalize_transcript_text(payload.get("transcript", ""))
    current_slide = request.session.get("current_slide", blank_slide())
    history = request.session.get("jarvis_history", [])

    result = run_jarvis_agent(message, current_slide=current_slide, transcript=transcript)
    request.session["current_slide"] = result.get("slide", current_slide)
    history.extend(
        [
            {"role": "user", "content": message},
            {"role": "assistant", "content": result.get("reply", "")},
        ]
    )
    request.session["jarvis_history"] = history[-30:]
    request.session.modified = True
    return _json_response(result)


@require_GET
def jarvis_skills(request: HttpRequest):
    """Return the current Jarvis skill catalog."""
    return _json_response({"skills": list_skills()})


@csrf_exempt
@require_POST
def import_jarvis_skill(request: HttpRequest):
    """Import a safe declarative skill file into the local catalog."""
    upload = request.FILES.get("skill")
    if upload is None:
        return HttpResponseBadRequest("skill file is required")
    try:
        skill = import_skill(upload.name, upload.read())
    except (ValueError, json.JSONDecodeError) as exc:
        return _json_response({"error": str(exc)}, status=400)
    return _json_response({"skill": skill, "skills": list_skills()})


@require_safe
def media_file(_request: HttpRequest, relative_path: str):
    """Serve generated Jarvis artifacts in local and container deployments."""
    media_root = settings.MEDIA_ROOT.resolve()
    target = (media_root / relative_path).resolve()
    if media_root not in target.parents or not target.is_file():
        raise Http404("File not found")
    mime_type, _encoding = mimetypes.guess_type(target.name)
    return FileResponse(target.open("rb"), content_type=mime_type or "application/octet-stream", as_attachment=False)

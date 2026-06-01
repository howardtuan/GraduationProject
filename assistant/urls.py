"""URL routes for the Talk2Draw assistant app."""

from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("health/", views.health, name="health"),
    # Legacy Flask-compatible endpoints kept so existing frontend calls continue to work.
    path("get_sentence_analyze", views.get_sentence_analyze, name="get_sentence_analyze"),
    path("get_dialogue_summary", views.get_dialogue_summary, name="get_dialogue_summary"),
    path("get_ppt", views.get_ppt, name="get_ppt"),
    path("SemanticAnalysis", views.semantic_analysis, name="semantic_analysis"),
    # New explicit endpoints for completed modules.
    path("api/search", views.smart_search, name="smart_search"),
    path("api/generate-image", views.generate_ai_image, name="generate_ai_image"),
    path("api/chart", views.chart_data, name="chart_data"),
    path("api/agent/chat", views.jarvis_chat, name="jarvis_chat"),
    path("api/agent/skills", views.jarvis_skills, name="jarvis_skills"),
    path("api/agent/skills/import", views.import_jarvis_skill, name="import_jarvis_skill"),
    path("media/<path:relative_path>", views.media_file, name="media_file"),
]

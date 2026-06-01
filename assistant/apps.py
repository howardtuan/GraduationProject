"""Application configuration for the assistant module."""

from django.apps import AppConfig


class AssistantConfig(AppConfig):
    """Register the app with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant"

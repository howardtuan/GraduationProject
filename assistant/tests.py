"""Regression tests for the Django rewrite."""

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .services import build_presentation_slide, classify_intent, extract_chart_data, generate_image, semantic_image_search


@override_settings(AI_PROVIDER="rules")
class ServiceFallbackTests(TestCase):
    """Verify that core features work without external API credentials."""

    def test_rule_based_intent_detects_search(self):
        result = classify_intent("幫我查小琉球最新新聞")
        self.assertEqual(result["intent"], "爬蟲模式")

    def test_general_photo_request_uses_web_search_not_album(self):
        result = classify_intent("給我看小琉球海龜照片")
        self.assertEqual(result["intent"], "爬蟲模式")

    def test_explicit_album_request_still_uses_local_catalog(self):
        result = classify_intent("請從相簿找我的花瓶岩照片")
        self.assertEqual(result["intent"], "相簿取圖")

    def test_image_generation_uses_web_reference_not_album_fallback(self):
        with patch("assistant.services.search_web", return_value={"images": [], "results": []}):
            result = generate_image("生成圖片：火星上的台灣夜市")
        self.assertEqual(result["source"], "web_reference")
        self.assertEqual(result["images"], [])

    def test_semantic_image_search_finds_album_asset(self):
        result = semantic_image_search("我想看花瓶岩")
        self.assertTrue(result["images"])
        self.assertIn("花瓶岩", result["images"][0]["filename"])

    def test_chart_data_extracts_two_values(self):
        result = extract_chart_data("五月銷售額20萬，六月銷售額90萬")
        self.assertEqual(result["labels"], ["五月", "六月"])
        self.assertEqual(result["values"], [200000.0, 900000.0])

    def test_presentation_fallback_returns_slide(self):
        result = build_presentation_slide("今天我要介紹的主題是小琉球之旅", {})
        self.assertFalse(result["should_exit"])
        self.assertEqual(result["slide"]["Title"], "小琉球之旅")


@override_settings(AI_PROVIDER="rules")
class ViewTests(TestCase):
    """Smoke-test the rendered page and Flask-compatible JSON endpoints."""

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "話中有畫")

    def test_sentence_analyze_endpoint(self):
        response = self.client.post(
            "/get_sentence_analyze",
            data=json.dumps({"inputParam": "進入簡報模式"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "簡報模式")

    def test_summary_endpoint(self):
        response = self.client.post(
            "/get_dialogue_summary",
            data=json.dumps({"inputParam": "今天討論小琉球旅遊。明天整理報告。"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("重點整理", response.json()["response"])


class JarvisAgentTests(TestCase):
    """Smoke-test Jarvis chat, artifact output, and skill importing."""

    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(AI_PROVIDER="rules", MEDIA_ROOT=Path(self.tmp_media.name))
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.tmp_media.cleanup()

    def test_jarvis_chat_routes_album_tool_only_when_explicit(self):
        response = self.client.post(
            "/api/agent/chat",
            data=json.dumps({"message": "請從相簿找花瓶岩"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["stage"]["type"], "images")
        self.assertTrue(payload["actions"])

    def test_jarvis_general_visual_request_routes_to_search(self):
        with patch("assistant.jarvis_agent.search_web", return_value={"results": [], "images": [], "source": "duckduckgo", "error": ""}):
            response = self.client.post(
                "/api/agent/chat",
                data=json.dumps({"message": "我想看花瓶岩照片"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["stage"]["type"], "search")

    def test_jarvis_can_return_downloadable_summary_file(self):
        response = self.client.post(
            "/api/agent/chat",
            data=json.dumps({"message": "把目前逐字稿整理成檔案傳給我", "transcript": "今天討論小琉球。明天整理報告。"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["attachments"])
        self.assertTrue(payload["attachments"][0]["url"].startswith("/media/generated/"))

    def test_jarvis_accepts_structured_transcript(self):
        response = self.client.post(
            "/api/agent/chat",
            data=json.dumps(
                {
                    "message": "幫我整理逐字稿成檔案",
                    "transcript": [{"role": "user", "content": "今天討論小琉球景點與圖表。"}],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        summary = response.json()["stage"]["summary"]
        self.assertIn("user: 今天討論小琉球景點與圖表", summary)
        self.assertNotIn("{'role'", summary)

    def test_import_skill_endpoint_adds_skill_to_catalog(self):
        upload = SimpleUploadedFile(
            "research-helper.md",
            b"---\nname: research-helper\ndescription: Help research topics\ntriggers: research, topic\n---\nUse search and summarize.",
            content_type="text/markdown",
        )
        response = self.client.post("/api/agent/skills/import", data={"skill": upload})
        self.assertEqual(response.status_code, 200)
        names = [skill["name"] for skill in response.json()["skills"]]
        self.assertIn("research-helper", names)

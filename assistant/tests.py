"""Regression tests for the Django rewrite."""

import json
from pathlib import Path
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .services import build_presentation_slide, classify_intent, extract_chart_data, semantic_image_search


@override_settings(OPENAI_API_KEY="")
class ServiceFallbackTests(TestCase):
    """Verify that core features work without external API credentials."""

    def test_rule_based_intent_detects_search(self):
        result = classify_intent("幫我查小琉球最新新聞")
        self.assertEqual(result["intent"], "爬蟲模式")

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


@override_settings(OPENAI_API_KEY="")
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
        self.settings_override = override_settings(OPENAI_API_KEY="", MEDIA_ROOT=Path(self.tmp_media.name))
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.tmp_media.cleanup()

    def test_jarvis_chat_routes_visual_tool(self):
        response = self.client.post(
            "/api/agent/chat",
            data=json.dumps({"message": "我想看花瓶岩"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["stage"]["type"], "images")
        self.assertTrue(payload["actions"])

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

# 話中有畫 Talk2Draw

「話中有畫」是將原本 Flask demo 重建為 Django 的畢業專題版本，目標是把口說內容即時轉成可理解的視覺資訊、網路檢索結果、簡報與對話大綱。

## 已完成模組

- 自然語言具象化：瀏覽器語音轉文字後，自動從本機相簿素材找出最接近語意的圖片。
- 即時智慧檢索：偵測查詢語意後，抓取 DuckDuckGo 輕量搜尋結果並呈現標題、摘要與連結。
- 對話彙整：將逐字稿整理為主題、大綱、重點整理與待辦事項，可下載文字檔。
- 口說簡報：進入簡報模式後，每句話會更新投影片標題、小標題、重點與圖片。
- AI 生圖：設定 `OPENAI_API_KEY` 後可呼叫 OpenAI 圖像模型；未設定時會改用本機相簿備援。
- 圖表模式：可把「五月銷售額20萬，六月90萬」這類口說資料轉成長條圖。
- Jarvis Agent：參考 OpenJarvis 的 webchat channel、工具路由、skill catalog 概念，整合成右側即時對話框。
- Skill 匯入：可匯入安全的 `.md` / `.json` / `.toml` skill 描述檔，Jarvis 會加入 catalog 並依觸發詞套用。

## 環境需求

- Python 3.10 以上
- Chrome 或 Edge 瀏覽器，語音辨識使用瀏覽器 Web Speech API
- OpenAI API key，正式 AI 摘要、簡報與生圖需要填入 `.env`

## Docker 快速啟動

建議優先用 Docker Compose 啟動。先確認 `.env` 已存在並填好 `OPENAI_API_KEY`：

```bash
cd /Users/hown-macmini/Desktop/Talk2Draw
docker compose up --build
```

開啟：

```text
http://127.0.0.1:8000/
```

背景執行：

```bash
docker compose up -d --build
```

停止：

```bash
docker compose down
```

清除容器資料庫與生成圖片：

```bash
docker compose down -v
```

Compose 會自動執行資料庫 migration，SQLite 會存到 `talk2draw_data` volume，AI 生圖產物會存到 `talk2draw_media` volume。

## 本機 Python 啟動

```bash
cd /Users/hown-macmini/Desktop/Talk2Draw
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

開啟：

```text
http://127.0.0.1:8000/
```

## `.env` 設定

只需要修改 `.env`，不需要改程式碼。

```env
DJANGO_SECRET_KEY=change-this-to-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SESSION_COOKIE_SECURE=False
DJANGO_CSRF_COOKIE_SECURE=False
DJANGO_SECURE_HSTS_SECONDS=0
SQLITE_DATABASE_PATH=db.sqlite3
OPENAI_API_KEY=你的 OpenAI API Key
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_IMAGE_SIZE=1024x1024
TALK2DRAW_SEARCH_TIMEOUT=8
```

本機測試可以先不填 `OPENAI_API_KEY`，系統會使用規則式備援；正式使用請務必填入。Docker Compose 會讀取同一份 `.env`，但會覆蓋部分 Django 安全設定，讓本機 `http://127.0.0.1:8000/` 可直接使用。

## 使用方式

1. 右側 `Mission Console` 可以直接輸入訊息給 Jarvis。
2. 按 `Voice` 可用瀏覽器語音辨識；第一次使用請允許麥克風權限。
3. 一般對話會自動進入自然語言具象化，左側會顯示相簿圖片。
4. 說或輸入「進入簡報模式」後，後續句子會更新投影片；「下一頁」會建立新頁。
5. 說「幫我查...」會進入即時智慧檢索，左側會顯示搜尋結果連結。
6. 說「幫我用 AI 產生...圖片」會進入 AI 生圖。
7. 說「五月銷售額20萬，六月90萬，做成圖表」會進入圖表模式。
8. 說「把目前逐字稿整理成檔案傳給我」會產生可下載的 Markdown 檔案。
9. 按 `Import` 可匯入 skill 檔，匯入後會顯示在 Skills 區塊。

## Skill 匯入格式

Jarvis 支援安全的宣告式 skill，不會執行外部腳本。建議使用 `SKILL.md` 風格：

```markdown
---
name: topic-briefing
description: Turn a topic into concise briefing notes
triggers: briefing, 簡報摘要, research
tags: research, summary
---
When invoked, search the topic and summarize it as concise briefing notes.
```

也可以匯入 OpenJarvis 常見的 TOML skill：

```toml
[skill]
name = "meeting-notes"
description = "Generate structured meeting notes from a transcript"
version = "0.1.0"
```

匯入後，Jarvis 會把 `name`、`triggers`、`tags` 加入觸發條件。基於安全性，目前只匯入 skill 描述與操作指引，不執行 skill 內的 shell/script。

## API 路徑

保留原 Flask demo 的路徑，前端與外部測試可直接沿用：

- `POST /get_sentence_analyze`：模式判斷，body: `{ "inputParam": "..." }`
- `POST /SemanticAnalysis`：本機相簿語意取圖
- `POST /get_ppt`：口說簡報生成
- `POST /get_dialogue_summary`：逐字稿摘要

新增完整功能路徑：

- `POST /api/search`：即時智慧檢索，body: `{ "query": "..." }`
- `POST /api/generate-image`：AI 生圖，body: `{ "prompt": "..." }`
- `POST /api/chart`：圖表資料萃取，body: `{ "text": "..." }`
- `POST /api/agent/chat`：Jarvis agent 對話，body: `{ "message": "...", "transcript": "..." }`
- `GET /api/agent/skills`：列出 built-in 與 imported skills
- `POST /api/agent/skills/import`：用 multipart form 上傳 skill 檔，欄位名為 `skill`
- `GET /media/generated/<file>`：下載 Jarvis 產出的檔案
- `GET /health/`：部署健康檢查

## 測試

```bash
source .venv/bin/activate
python manage.py test
```

測試不需要 OpenAI key，會走規則式備援。

Docker 容器內測試：

```bash
docker compose run --rm app python manage.py test
```

## 專案結構

```text
assistant/
  jarvis_agent.py    OpenJarvis-style agent、skill catalog、附件產出
  image_catalog.py   本機相簿圖片索引與語意搜尋
  prompts.py         OpenAI 提示詞集中管理
  services.py        摘要、模式判斷、簡報、生圖、檢索、圖表邏輯
  views.py           Django JSON API 與頁面 view
talk2draw_project/
  settings.py        Django 設定，讀取 .env
  urls.py            根路由
templates/index.html 主操作介面
static/css/app.css   前端樣式
static/js/app.js     語音辨識、API 呼叫與畫面渲染
static/images/       專題相簿素材
Dockerfile           Django/Gunicorn 容器建置
docker-compose.yml   本機容器編排
docker/entrypoint.sh 容器啟動時自動 migrate
```

## 部署注意事項

- `DJANGO_DEBUG=False` 時請設定正式 `DJANGO_SECRET_KEY` 與 `DJANGO_ALLOWED_HOSTS`。
- 正式 HTTPS 部署建議把 `DJANGO_SECURE_SSL_REDIRECT`、`DJANGO_SESSION_COOKIE_SECURE`、`DJANGO_CSRF_COOKIE_SECURE` 設為 `True`，並設定 `DJANGO_SECURE_HSTS_SECONDS=31536000`。
- 執行 `python manage.py collectstatic` 後，用 Gunicorn 啟動：

```bash
gunicorn talk2draw_project.wsgi:application
```

- 不要提交 `.env`、`.venv/`、`node_modules/` 或任何金鑰 JSON。

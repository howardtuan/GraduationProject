// Jarvis console controller: webchat, speech input, tool rendering, and skills.
(() => {
  const state = {
    transcript: "",
    lastMessage: "",
    currentSlide: null,
    recognition: null,
    listening: false,
    micEnabled: true,
    autoStartAttempted: false,
    skills: [],
  };

  const els = {
    statusText: document.querySelector("#statusText"),
    modePill: document.querySelector("#modePill"),
    stageContent: document.querySelector("#stageContent"),
    micState: document.querySelector("#micState"),
    chatFeed: document.querySelector("#chatFeed"),
    jarvisInput: document.querySelector("#jarvisInput"),
    sendBtn: document.querySelector("#sendBtn"),
    voiceBtn: document.querySelector("#voiceBtn"),
    stopVoiceBtn: document.querySelector("#stopVoiceBtn"),
    clearBtn: document.querySelector("#clearBtn"),
    summaryBtn: document.querySelector("#summaryBtn"),
    transcriptOutput: document.querySelector("#transcriptOutput"),
    summaryOutput: document.querySelector("#summaryOutput"),
    downloadTranscriptBtn: document.querySelector("#downloadTranscriptBtn"),
    downloadSummaryBtn: document.querySelector("#downloadSummaryBtn"),
    skillInput: document.querySelector("#skillInput"),
    skillsList: document.querySelector("#skillsList"),
    skillCount: document.querySelector("#skillCount"),
    showSkillsStageBtn: document.querySelector("#showSkillsStageBtn"),
  };

  const csrfToken = document.querySelector("meta[name='csrf-token']")?.content || "";

  function setStatus(message) {
    els.statusText.textContent = message;
  }

  function setMode(mode) {
    els.modePill.textContent = mode && mode !== "None" ? mode : "standby";
  }

  function setMicState(message, active = false) {
    els.micState.textContent = message;
    document.body.classList.toggle("mic-active", active);
    const speechAvailable = Boolean(state.recognition);
    els.voiceBtn.disabled = !speechAvailable || active;
    els.stopVoiceBtn.disabled = !speechAvailable || (!active && !state.micEnabled);
  }

  function escapeHTML(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error((await response.text()) || `HTTP ${response.status}`);
    }
    return response.json();
  }

  function appendTranscript(text) {
    state.lastMessage = text;
    state.transcript = state.transcript ? `${state.transcript}\nUser：${text}` : `User：${text}`;
    els.transcriptOutput.textContent = state.transcript;
  }

  function appendMessage(role, content, options = {}) {
    const article = document.createElement("article");
    article.className = `message ${role}`;
    const avatar = role === "user" ? "U" : "J";
    const actions = options.actions || [];
    const attachments = options.attachments || [];
    article.innerHTML = `
      <div class="avatar">${avatar}</div>
      <div class="bubble">
        ${escapeHTML(content)}
        ${actions.length ? `<div class="action-list">${actions.map((item) => `
          <span>${escapeHTML(item.tool)} · ${escapeHTML(item.status)}${item.detail ? ` · ${escapeHTML(item.detail)}` : ""}</span>
        `).join("")}</div>` : ""}
        ${attachments.length ? `<div class="attachment-list">${attachments.map((item) => `
          <a href="${escapeHTML(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.name)}</a>
        `).join("")}</div>` : ""}
      </div>
    `;
    els.chatFeed.appendChild(article);
    els.chatFeed.scrollTop = els.chatFeed.scrollHeight;
  }

  function renderEmpty(title = "Awaiting command", subtitle = "Send a message to Jarvis. Tool output will assemble here.") {
    els.stageContent.innerHTML = `
      <div class="empty-state">
        <strong>${escapeHTML(title)}</strong>
        <span>${escapeHTML(subtitle)}</span>
      </div>
    `;
  }

  function renderImages(images = [], message = "") {
    if (!images.length) {
      renderEmpty("No visual match", "Jarvis could not find a close local album image.");
      return;
    }
    els.stageContent.innerHTML = `
      <div class="image-grid">
        ${images.map((image) => `
          <figure class="image-tile">
            <img src="${escapeHTML(image.url)}" alt="${escapeHTML((image.keywords || [image.filename]).join("、"))}">
            <figcaption>${escapeHTML((image.keywords || [image.filename]).slice(0, 3).join("、"))}</figcaption>
          </figure>
        `).join("")}
      </div>
      ${message ? `<p class="module-message">${escapeHTML(message)}</p>` : ""}
    `;
  }

  function renderGeneratedImage(data) {
    const images = data.images || [];
    if (!images.length) {
      renderEmpty("No web reference images", data.message || "No image returned.");
      return;
    }
    els.stageContent.innerHTML = `
      <section class="reference-stage">
        <div class="stage-intro">
          <strong>Web image references</strong>
          <span>${escapeHTML(data.message || "已整理網路相關圖片作為視覺參考。")}</span>
        </div>
        ${webImageGridHTML(images)}
        ${searchResultsHTML(data.results || [], "Related sources")}
      </section>
    `;
  }

  function webImageGridHTML(images = []) {
    if (!images.length) return "";
    return `
      <div class="web-image-grid">
        ${images.map((image) => `
          <figure class="web-image-card">
            <img src="${escapeHTML(image.url)}" alt="${escapeHTML(image.title || image.source_title || "web reference image")}" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('figure').classList.add('is-broken')">
            <figcaption>
              <span>${escapeHTML(image.title || image.source_title || "Web image")}</span>
              ${image.source_url ? `<a href="${escapeHTML(image.source_url)}" target="_blank" rel="noopener noreferrer">Source</a>` : ""}
            </figcaption>
          </figure>
        `).join("")}
      </div>
    `;
  }

  function searchResultsHTML(results = [], title = "") {
    if (!results.length) return "";
    return `
      <div class="search-results">
        ${title ? `<h3>${escapeHTML(title)}</h3>` : ""}
        ${results.map((item) => `
          <a class="search-item" href="${escapeHTML(item.url)}" target="_blank" rel="noopener noreferrer">
            <strong>${escapeHTML(item.title)}</strong>
            <span>${escapeHTML(item.snippet || item.url)}</span>
          </a>
        `).join("")}
      </div>
    `;
  }

  function renderSlide(slide = {}, images = []) {
    const title = slide.Title || "Untitled slide";
    const littleTitles = slide.LittleTitle || [];
    const content = slide.Content || [];
    els.stageContent.innerHTML = `
      <article class="slide-card">
        <h2>${escapeHTML(title)}</h2>
        <div class="slide-body">
          <div>
            ${littleTitles.length ? `<ul class="topic-list">${littleTitles.map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>` : ""}
            ${content.length ? `<div class="content-list">${content.map((item) => `<p>${escapeHTML(item)}</p>`).join("")}</div>` : ""}
          </div>
          <div class="slide-images">
            ${images.map((image) => `<img src="${escapeHTML(image.url)}" alt="${escapeHTML(image.filename)}">`).join("")}
          </div>
        </div>
      </article>
    `;
  }

  function renderSearchResults(data = {}) {
    const results = data.results || [];
    const images = data.images || [];
    if (!results.length) {
      renderEmpty("No search results", data.error || "The retrieval channel returned no usable links.");
      return;
    }
    els.stageContent.innerHTML = `
      <section class="search-layout">
        ${images.length ? `
          <div class="stage-intro">
            <strong>Research visuals</strong>
            <span>從最相關的網路來源抽出的圖片參考。</span>
          </div>
          ${webImageGridHTML(images)}
        ` : ""}
        ${searchResultsHTML(results, "Search results")}
      </section>
    `;
  }

  function renderChart(data = {}) {
    const labels = data.labels || [];
    const values = data.values || [];
    if (!labels.length) {
      renderEmpty("Chart needs data", "Give Jarvis at least two numeric values.");
      return;
    }
    const max = Math.max(...values, 1);
    els.stageContent.innerHTML = `
      <div class="chart-panel">
        ${labels.map((label, index) => {
          const value = values[index];
          const width = Math.max((value / max) * 100, 4);
          return `
            <div class="bar-row">
              <span>${escapeHTML(label)}</span>
              <div class="bar-track"><span class="bar-fill" style="width:${width}%"></span></div>
              <strong>${escapeHTML(formatNumber(value))}</strong>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }

  function renderSkills(skills = []) {
    els.stageContent.innerHTML = `
      <div class="skills-stage">
        ${skills.map((skill) => skillDetailsHTML(skill, "skill-card")).join("")}
      </div>
    `;
  }

  function skillDetailsHTML(skill, className = "skill-item") {
    const triggers = skill.trigger_phrases || [];
    const tags = skill.tags || [];
    return `
      <details class="${className}">
        <summary>
          <span>${escapeHTML(skill.name)}</span>
          <small>${escapeHTML(skill.source || "local")}</small>
        </summary>
        <p>${escapeHTML(skill.description || "No description")}</p>
        <dl>
          <div><dt>Version</dt><dd>${escapeHTML(skill.version || "0.1.0")}</dd></div>
          <div><dt>Triggers</dt><dd>${escapeHTML(triggers.length ? triggers.join("、") : "未設定")}</dd></div>
          <div><dt>Tags</dt><dd>${escapeHTML(tags.length ? tags.join("、") : "未設定")}</dd></div>
        </dl>
      </details>
    `;
  }

  function renderSkillsList(skills = []) {
    if (!skills.length) {
      els.skillsList.innerHTML = `<span class="skills-empty">No skills loaded</span>`;
      return;
    }
    els.skillsList.innerHTML = skills.map((skill) => skillDetailsHTML(skill)).join("");
  }

  function renderSummary(summary = "") {
    els.stageContent.innerHTML = `<div class="summary-stage"><pre>${escapeHTML(summary)}</pre></div>`;
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 1 }).format(value);
  }

  function renderAgentStage(stage = {}) {
    if (stage.type === "images") renderImages(stage.images || [], stage.message || "");
    else if (stage.type === "generated_image") renderGeneratedImage(stage);
    else if (stage.type === "search") renderSearchResults(stage);
    else if (stage.type === "chart") renderChart(stage);
    else if (stage.type === "slide") renderSlide(stage.slide, stage.images || []);
    else if (stage.type === "summary") renderSummary(stage.summary || "");
    else if (stage.type === "skills") renderSkills(stage.skills || []);
    else renderEmpty();
  }

  async function sendToJarvis(rawText) {
    const text = rawText.trim();
    if (!text) return;
    appendMessage("user", text);
    appendTranscript(text);
    setStatus("Jarvis is routing tools...");
    els.sendBtn.disabled = true;

    try {
      const result = await postJSON("/api/agent/chat", {
        message: text,
        transcript: state.transcript,
        currentSlide: state.currentSlide,
      });
      state.currentSlide = result.slide || state.currentSlide;
      setMode(result.mode || "standby");
      appendMessage("assistant", result.reply || "Done.", {
        actions: result.actions || [],
        attachments: result.attachments || [],
      });
      renderAgentStage(result.stage || {});
      setStatus("Jarvis online");
    } catch (error) {
      appendMessage("assistant", `系統回報錯誤：${error.message}`);
      setStatus("Error");
    } finally {
      els.sendBtn.disabled = false;
    }
  }

  async function loadSkills() {
    try {
      const response = await fetch("/api/agent/skills");
      const data = await response.json();
      const skills = data.skills || [];
      state.skills = skills;
      els.skillCount.textContent = `${skills.length} loaded`;
      renderSkillsList(skills);
    } catch (_error) {
      els.skillCount.textContent = "offline";
      els.skillsList.innerHTML = `<span class="skills-empty">Skill catalog offline</span>`;
    }
  }

  async function importSkill(file) {
    const formData = new FormData();
    formData.append("skill", file);
    setStatus("Importing skill...");
    const response = await fetch("/api/agent/skills/import", {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Skill import failed");
    }
    appendMessage("assistant", `Skill imported: ${data.skill.name}`);
    await loadSkills();
    renderSkills(data.skills || []);
    setStatus("Jarvis online");
  }

  function currentTextForTool() {
    return els.jarvisInput.value.trim() || state.lastMessage;
  }

  async function routeToolbar(view) {
    const text = currentTextForTool();
    if (!text) {
      renderEmpty("Awaiting command", "Type or speak before forcing a tool route.");
      return;
    }
    if (view === "visual") await sendToJarvis(`找相簿圖片：${text}`);
    if (view === "slide") await sendToJarvis(`進入簡報模式，${text}`);
    if (view === "search") await sendToJarvis(`幫我查：${text}`);
    if (view === "chart") await sendToJarvis(`做成圖表：${text}`);
  }

  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      els.voiceBtn.disabled = true;
      els.stopVoiceBtn.disabled = true;
      state.micEnabled = false;
      setMicState("Mic unavailable", false);
      setStatus("Voice unavailable; text console ready");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "zh-TW";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      const transcript = result[0].transcript.trim();
      if (result.isFinal && transcript) {
        sendToJarvis(transcript);
      } else if (transcript) {
        els.jarvisInput.value = transcript;
      }
    };
    recognition.onend = () => {
      state.listening = false;
      if (state.micEnabled) {
        setMicState("Mic restarting", false);
        window.setTimeout(() => startListening(), 350);
      } else {
        setMicState("Mic off", false);
        setStatus("Jarvis online");
      }
    };
    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        state.micEnabled = false;
        setMicState("Mic permission needed", false);
      }
      setStatus(`Voice error: ${event.error}`);
    };
    state.recognition = recognition;
    setMicState("Mic ready", false);
  }

  function startListening() {
    if (!state.recognition || state.listening) return;
    state.micEnabled = true;
    try {
      state.recognition.start();
      state.listening = true;
      setMicState("Mic listening", true);
      setStatus("Listening...");
    } catch (_error) {
      setMicState("Mic ready", false);
    }
  }

  function stopListening() {
    state.micEnabled = false;
    if (state.recognition && state.listening) {
      state.recognition.stop();
    }
    state.listening = false;
    setMicState("Mic off", false);
    setStatus("Jarvis online");
  }

  function downloadText(filename, text) {
    const blob = new Blob([text || ""], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function bindEvents() {
    els.sendBtn.addEventListener("click", () => {
      const text = els.jarvisInput.value;
      els.jarvisInput.value = "";
      sendToJarvis(text);
    });
    els.jarvisInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        els.sendBtn.click();
      }
    });
    els.clearBtn.addEventListener("click", () => {
      state.transcript = "";
      state.lastMessage = "";
      els.transcriptOutput.textContent = "";
      els.summaryOutput.textContent = "尚未生成";
      els.chatFeed.innerHTML = "";
      appendMessage("assistant", "Console cleared. Jarvis online.");
      renderEmpty();
      setMode("standby");
    });
    els.voiceBtn.addEventListener("click", () => startListening());
    els.stopVoiceBtn.addEventListener("click", () => stopListening());
    els.summaryBtn.addEventListener("click", async () => {
      const data = await postJSON("/get_dialogue_summary", { inputParam: state.transcript });
      els.summaryOutput.textContent = data.response;
      renderSummary(data.response);
    });
    els.downloadTranscriptBtn.addEventListener("click", () => downloadText("transcript.txt", state.transcript));
    els.downloadSummaryBtn.addEventListener("click", () => downloadText("outline.txt", els.summaryOutput.textContent));
    els.skillInput.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        await importSkill(file);
      } catch (error) {
        appendMessage("assistant", `Skill import failed: ${error.message}`);
        setStatus("Skill import failed");
      } finally {
        event.target.value = "";
      }
    });
    els.showSkillsStageBtn.addEventListener("click", () => renderSkills(state.skills));
    document.querySelectorAll("[data-prompt]").forEach((button) => {
      button.addEventListener("click", () => sendToJarvis(button.dataset.prompt || ""));
    });
    document.querySelectorAll("[data-view]").forEach((button) => {
      button.addEventListener("click", () => routeToolbar(button.dataset.view));
    });
  }

  initSpeechRecognition();
  bindEvents();
  loadSkills();
  setMode("standby");
  window.setTimeout(() => {
    state.autoStartAttempted = true;
    startListening();
  }, 450);
})();

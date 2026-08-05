const messages = document.querySelector("#messages");
const statusText = document.querySelector("#status");
const chatForm = document.querySelector("#chatForm");
const promptInput = document.querySelector("#promptInput");
const sendButton = document.querySelector("#sendButton");
const suggestions = document.querySelector("#suggestions");
const fileInput = document.querySelector("#fileInput");
const uploadButton = document.querySelector("#uploadButton");
const assetsButton = document.querySelector("#assetsButton");
const filesPanel = document.querySelector("#filesPanel");
const filesList = document.querySelector("#filesList");
const closeFiles = document.querySelector("#closeFiles");
const settingsPanel = document.querySelector("#settingsPanel");
const settingsButton = document.querySelector("#settingsButton");
const closeSettings = document.querySelector("#closeSettings");
const ssidInput = document.querySelector("#ssidInput");
const passwordInput = document.querySelector("#passwordInput");
const saveSettings = document.querySelector("#saveSettings");
const voiceButton = document.querySelector("#voiceButton");
const ttsButton = document.querySelector("#ttsButton");
const clearButton = document.querySelector("#clearButton");

let commands = [];
let recognition = null;
let ttsEnabled = true;
let isListening = false;

const voiceSupported = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechSupported = typeof window.speechSynthesis !== "undefined";

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMarkdown(text) {
  if (!text) return "";
  const safeText = escapeHtml(text);
  const codeBlocks = [];
  const inlineCodes = [];

  const withoutBlocks = safeText.replace(/```(?:[^\n]*\n)?([\s\S]*?)```/g, (_, code) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(`<pre><code>${code}</code></pre>`);
    return placeholder;
  });

  const withoutInline = withoutBlocks.replace(/`([^`]+)`/g, (_, code) => {
    const placeholder = `__INLINE_CODE_${inlineCodes.length}__`;
    inlineCodes.push(`<code>${code}</code>`);
    return placeholder;
  });

  let formatted = withoutInline;
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  formatted = formatted.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  formatted = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  formatted = formatted.replace(/^>\s?(.*)$/gm, "<blockquote>$1</blockquote>");

  codeBlocks.forEach((block, index) => {
    formatted = formatted.replace(`__CODE_BLOCK_${index}__`, block);
  });
  inlineCodes.forEach((code, index) => {
    formatted = formatted.replace(`__INLINE_CODE_${index}__`, code);
  });

  const paragraphs = formatted
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => paragraph.replace(/\n/g, "<br>"));

  return paragraphs.map((p) => `<p>${p}</p>`).join("");
}

function addMessage(role, text, files = []) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.innerHTML = renderMarkdown(text);

  for (const file of files) {
    const link = document.createElement("a");
    link.href = file.download_url;
    link.textContent = `Download ${file.name}`;
    link.target = "_blank";
    link.rel = "noreferrer";
    bubble.appendChild(link);
  }

  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

function setStatus(text, warning = false) {
  statusText.textContent = text;
  statusText.style.color = warning ? "#ffb347" : "";
}

async function loadStatus() {
  try {
    const response = await fetch("/health");
    const data = await response.json();
    setStatus(data.ok ? "Connected to TutorBot" : "TutorBot unavailable", !data.ok);
  } catch {
    setStatus("TutorBot server not reachable", true);
  }
}

async function loadCommands() {
  try {
    const response = await fetch("/commands");
    const data = await response.json();
    commands = data.commands || [];
    renderSuggestions("");
  } catch {
    commands = [];
  }
}

function renderSuggestions(value) {
  suggestions.innerHTML = "";
  const normalized = value.trim().toLowerCase();
  const matches = commands
    .filter((command) => !normalized || command.name.startsWith(normalized))
    .slice(0, 8);

  for (const command of matches) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "suggestion";
    item.textContent = command.usage;
    item.title = command.description;
    item.addEventListener("click", () => {
      promptInput.value = command.name + " ";
      promptInput.focus();
    });
    suggestions.appendChild(item);
  }
}

function updateFilesList(files) {
  filesList.innerHTML = "";
  if (!files.length) {
    filesList.innerHTML = "<li class=\"empty\">No files uploaded yet.</li>";
    return;
  }

  for (const file of files) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = file.download_url;
    link.textContent = file.name;
    link.target = "_blank";
    link.rel = "noreferrer";
    item.appendChild(link);
    item.insertAdjacentHTML("beforeend", `<span class=\"file-size\">${file.size} bytes</span>`);
    filesList.appendChild(item);
  }
}

async function loadFiles() {
  try {
    const response = await fetch("/files");
    const data = await response.json();
    updateFilesList(data.files || []);
  } catch (error) {
    updateFilesList([]);
    addMessage("error", `Failed to list files: ${error.message}`);
  }
}

function showFilesPanel() {
  filesPanel.classList.remove("hidden");
  filesPanel.setAttribute("aria-hidden", "false");
  loadFiles();
}

function hideFilesPanel() {
  filesPanel.classList.add("hidden");
  filesPanel.setAttribute("aria-hidden", "true");
}

function initSpeechRecognition() {
  if (!voiceSupported) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.addEventListener("result", (event) => {
    const transcript = event.results[0][0].transcript;
    promptInput.value = transcript;
    promptInput.focus();
    stopListening();
  });

  recognition.addEventListener("end", stopListening);
  recognition.addEventListener("error", () => stopListening());
}

function startListening() {
  if (!recognition) {
    addMessage("system", "Voice input is not supported by this browser.");
    return;
  }
  isListening = true;
  voiceButton.classList.add("listening");
  voiceButton.textContent = "🎧";
  recognition.start();
}

function stopListening() {
  isListening = false;
  voiceButton.classList.remove("listening");
  voiceButton.textContent = "🎙";
}

function toggleTts() {
  ttsEnabled = !ttsEnabled;
  ttsButton.classList.toggle("active", ttsEnabled);
  ttsButton.textContent = ttsEnabled ? "🔊" : "🔇";
}

function speakText(text) {
  if (!speechSupported || !ttsEnabled) return;
  if (!text.trim()) return;
  const utterance = new SpeechSynthesisUtterance(text.replace(/\s+/g, " ").trim());
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

async function sendPrompt(prompt) {
  sendButton.disabled = true;
  addMessage("user", prompt);
  addMessage("system", "Thinking...");

  try {
    const response = await fetch("/ai-chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({prompt}),
    });
    const data = await response.json();
    messages.lastChild.remove();

    if (!response.ok) {
      addMessage("error", data.error || "TutorBot request failed.");
      return;
    }

    addMessage(data.type || "assistant", data.response || "", data.files || []);
    speakText(data.response || "");
  } catch (error) {
    messages.lastChild.remove();
    addMessage("error", `Network error: ${error.message}`);
  } finally {
    sendButton.disabled = false;
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;
  promptInput.value = "";
  renderSuggestions("");
  sendPrompt(prompt);
});

promptInput.addEventListener("input", () => {
  if (promptInput.value.startsWith("/")) {
    renderSuggestions(promptInput.value);
  } else {
    suggestions.innerHTML = "";
  }
});

voiceButton.addEventListener("click", () => {
  if (isListening) {
    recognition.stop();
  } else {
    startListening();
  }
});

ttsButton.addEventListener("click", toggleTts);
closeFiles.addEventListener("click", hideFilesPanel);
assetsButton.addEventListener("click", showFilesPanel);
clearButton.addEventListener("click", async () => {
  try {
    await fetch("/clear", {method: "POST"});
    messages.innerHTML = "";
    addMessage("system", "Conversation cleared.");
  } catch {
    addMessage("error", "Unable to clear chat on the server.");
  }
});

uploadButton.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) {
    addMessage("error", "Choose a file first.");
    return;
  }

  uploadButton.disabled = true;
  const body = new FormData();
  body.append("file", file);

  try {
    const response = await fetch("/files", {method: "POST", body});
    const data = await response.json();
    if (!response.ok) {
      addMessage("error", data.error || "Upload failed.");
      return;
    }
    addMessage("system", `Uploaded **${data.filename}** (${data.size} bytes).`, [
      {name: data.filename, download_url: data.download_url},
    ]);
    fileInput.value = "";
    loadFiles();
  } catch (error) {
    addMessage("error", `Upload failed: ${error.message}`);
  } finally {
    uploadButton.disabled = false;
  }
});

function openSettings() {
  settingsPanel.classList.add("open");
  settingsPanel.setAttribute("aria-hidden", "false");
}

function hideSettings() {
  settingsPanel.classList.remove("open");
  settingsPanel.setAttribute("aria-hidden", "true");
}

settingsButton.addEventListener("click", async () => {
  openSettings();
  try {
    const response = await fetch("/esp32/settings");
    const data = await response.json();
    ssidInput.value = data.ssid || "";
    passwordInput.value = "";
  } catch {
    addMessage("error", "Could not load ESP32 settings.");
  }
});

closeSettings.addEventListener("click", hideSettings);

saveSettings.addEventListener("click", async () => {
  const ssid = ssidInput.value.trim();
  const password = passwordInput.value;

  try {
    const response = await fetch("/esp32/settings", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ssid, password}),
    });
    const data = await response.json();
    if (!response.ok) {
      addMessage("error", data.error || "Could not save settings.");
      return;
    }
    addMessage("system", `Saved ESP32 Wi-Fi settings for ${data.ssid}.`);
    hideSettings();
  } catch (error) {
    addMessage("error", `Could not save settings: ${error.message}`);
  }
});

if (voiceSupported) {
  initSpeechRecognition();
} else {
  voiceButton.disabled = true;
  voiceButton.title = "Voice input not supported in this browser";
}

if (!speechSupported) {
  ttsButton.disabled = true;
  ttsButton.title = "Speech output not supported in this browser";
}

addMessage("system", "Welcome to TutorBot. Ask a question or use /help.");
loadStatus();
loadCommands();

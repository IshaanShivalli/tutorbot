const messages = document.querySelector("#messages");
const statusText = document.querySelector("#status");
const chatForm = document.querySelector("#chatForm");
const promptInput = document.querySelector("#promptInput");
const sendButton = document.querySelector("#sendButton");
const suggestions = document.querySelector("#suggestions");
const fileInput = document.querySelector("#fileInput");
const uploadButton = document.querySelector("#uploadButton");
const settingsPanel = document.querySelector("#settingsPanel");
const settingsButton = document.querySelector("#settingsButton");
const closeSettings = document.querySelector("#closeSettings");
const ssidInput = document.querySelector("#ssidInput");
const passwordInput = document.querySelector("#passwordInput");
const saveSettings = document.querySelector("#saveSettings");

let commands = [];

function addMessage(role, text, files = []) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = text;

  for (const file of files) {
    const link = document.createElement("a");
    link.href = file.download_url;
    link.textContent = `\nDownload ${file.name}`;
    link.target = "_blank";
    bubble.appendChild(link);
  }

  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

async function loadStatus() {
  try {
    const response = await fetch("/health");
    const data = await response.json();
    statusText.textContent = data.ok ? "Connected to TutorBot" : "TutorBot unavailable";
  } catch {
    statusText.textContent = "TutorBot server not reachable";
  }
}

async function loadCommands() {
  const response = await fetch("/commands");
  const data = await response.json();
  commands = data.commands || [];
  renderSuggestions("");
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
    addMessage("system", `Uploaded ${data.filename} (${data.size} bytes).`, [
      {name: data.filename, download_url: data.download_url},
    ]);
    fileInput.value = "";
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

addMessage("system", "Welcome to TutorBot. Ask a question or use /help.");
loadStatus();
loadCommands();

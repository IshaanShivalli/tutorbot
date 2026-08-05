const messages = document.querySelector("#messages");
const statusText = document.querySelector("#status");
const chatForm = document.querySelector("#chatForm");
const promptInput = document.querySelector("#promptInput");
const sendButton = document.querySelector("#sendButton");
const suggestions = document.querySelector("#suggestions");
const fileInput = document.querySelector("#fileInput");
const filesPanel = document.querySelector("#filesPanel");
const filesList = document.querySelector("#filesList");
const closeFiles = document.querySelector("#closeFiles");
const settingsPanel = document.querySelector("#settingsPanel");
const settingsButton = document.querySelector("#settingsButton");
const closeSettings = document.querySelector("#closeSettings");
const ssidInput = document.querySelector("#ssidInput");
const passwordInput = document.querySelector("#passwordInput");
const languageSelect = document.querySelector("#languageSelect");
const learningLanguageSelect = document.querySelector("#learningLanguageSelect");
const saveSettings = document.querySelector("#saveSettings");
const voiceButton = document.querySelector("#voiceButton");
const ttsButton = document.querySelector("#ttsButton");
const clearButton = document.querySelector("#clearButton");
const profileText = document.querySelector("#profileText");
const changeFocusButton = document.querySelector("#changeFocusButton");
const focusModal = document.querySelector("#focusModal");
const closeFocusModal = document.querySelector("#closeFocusModal");
const gradeSelect = document.querySelector("#gradeSelect");
const subjectSelect = document.querySelector("#subjectSelect");
const saveFocusButton = document.querySelector("#saveFocusButton");
const cameraPanel = document.querySelector("#cameraPanel");
const cameraPreview = document.querySelector("#cameraPreview");
const captureButton = document.querySelector("#captureButton");
const cancelCameraButton = document.querySelector("#cancelCameraButton");
const uploadMenuButton = document.querySelector("#uploadMenuButton");
const uploadMenu = document.querySelector("#uploadMenu");
const menuUploadImage = document.querySelector("#menuUploadImage");
const menuUseCamera = document.querySelector("#menuUseCamera");
const menuProcessImage = document.querySelector("#menuProcessImage");
const menuFiles = document.querySelector("#menuFiles");
const filesInput = document.querySelector("#filesInput");

let commands = [];
let recognition = null;
let ttsEnabled = true;
let isListening = false;
let cameraStream = null;
let capturedImageBlob = null;

const voiceSupported = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechSupported = typeof window.speechSynthesis !== "undefined";

const languageMap = {
  English: "en-US",
  Spanish: "es-ES",
  French: "fr-FR",
  German: "de-DE",
  Chinese: "zh-CN",
  Portuguese: "pt-BR",
  Japanese: "ja-JP",
  Russian: "ru-RU",
  Arabic: "ar-SA",
  Hindi: "hi-IN",
};

function getSelectedInterfaceLanguage() {
  return languageSelect?.value || localStorage.getItem("tutorbot_interface_language") || "English";
}

function getSelectedLearningLanguage() {
  return learningLanguageSelect?.value || localStorage.getItem("tutorbot_learning_language") || "English";
}

function getLanguageCode(language) {
  return languageMap[language] || "en-US";
}

function loadLanguageSelection() {
  const interfaceLanguage = localStorage.getItem("tutorbot_interface_language") || "English";
  const learningLanguage = localStorage.getItem("tutorbot_learning_language") || "English";
  if (languageSelect) {
    languageSelect.value = interfaceLanguage;
  }
  if (learningLanguageSelect) {
    learningLanguageSelect.value = learningLanguage;
  }
}

function saveLanguageSelection() {
  const interfaceLanguage = getSelectedInterfaceLanguage();
  const learningLanguage = getSelectedLearningLanguage();
  localStorage.setItem("tutorbot_interface_language", interfaceLanguage);
  localStorage.setItem("tutorbot_learning_language", learningLanguage);
  return learningLanguage;
}

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
  const container = document.createElement("div");
  container.className = `message-container ${role}`;
  
  // Add avatar for assistant messages
  if (role === "assistant" || role === "system") {
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "🤖";
    container.appendChild(avatar);
  }
  
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
  
  container.appendChild(bubble);
  messages.appendChild(container);
  messages.scrollTop = messages.scrollHeight;
}

function setStatus(text, warning = false) {
  statusText.textContent = text;
  statusText.style.color = warning ? "#ffb347" : "";
}

async function loadStatus() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      setStatus("TutorBot server not reachable", true);
      return;
    }
    const data = await response.json();
    setStatus(data.ok ? "Connected to TutorBot" : "TutorBot unavailable", !data.ok);
  } catch (error) {
    console.error("Status check failed:", error);
    setStatus("TutorBot server not reachable", true);
  }
}

async function loadCommands() {
  try {
    const response = await fetch("/commands");
    const data = await response.json();
    commands = data.commands || [];
  } catch {
    commands = [];
  }
}

function normalizeSearchText(value) {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

function renderSuggestions(value) {
  suggestions.innerHTML = "";
  const normalized = normalizeSearchText(value);
  if (!normalized) return;

  const matches = commands
    .filter((command) => {
      const name = normalizeSearchText(command.name);
      const usage = normalizeSearchText(command.usage);
      return name.includes(normalized) || usage.includes(normalized);
    })
    .slice(0, 12);

  if (value.trim() === "/") {
    const header = document.createElement("div");
    header.className = "suggestions-header";
    header.textContent = "Available commands";
    suggestions.appendChild(header);
  }

  for (const command of matches) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "suggestion";
    item.innerHTML = `<strong>${escapeHtml(command.usage)}</strong><br><small>${escapeHtml(command.description)}</small>`;
    item.title = command.description;
    item.addEventListener("click", () => {
      promptInput.value = command.name + " ";
      promptInput.focus();
      renderSuggestions(promptInput.value);
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
  recognition.lang = getLanguageCode(getSelectedLearningLanguage());
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

function updateSpeechRecognitionLanguage() {
  if (!recognition || !voiceSupported) return;
  recognition.lang = getLanguageCode(getSelectedLearningLanguage());
}

async function processSelectedImage() {
  const file = fileInput.files?.[0] || null;
  const imageFile = capturedImageBlob || file;
  if (!imageFile) {
    addMessage("error", "Choose an image or capture one with the camera before processing.");
    return;
  }
  if (file && !file.type.startsWith("image/")) {
    addMessage("error", "Only image files can be processed.");
    return;
  }

  addMessage("user", "[Image selected for processing]");
  addMessage("system", "Analyzing image...");

  const body = new FormData();
  if (capturedImageBlob) {
    body.append("image", capturedImageBlob, "capture.jpg");
  } else {
    body.append("image", file);
  }
  body.append("language", getSelectedLearningLanguage());
  body.append(
    "profile",
    JSON.stringify({
      grade: localStorage.getItem("tutorbot_grade") || "Grade 9",
      subject: localStorage.getItem("tutorbot_subject") || "General",
    })
  );

  try {
    const response = await fetch("/process-image", {method: "POST", body});
    const data = await response.json();
    messages.lastChild.remove();

    if (!response.ok) {
      addMessage("error", data.error || "Image processing failed.");
      return;
    }

    addMessage(data.type || "assistant", data.response || "", data.files || []);
    if (data.ocr_text) {
      addMessage("system", `OCR detected:\n${data.ocr_text}`);
    }
    if (data.image_description) {
      addMessage("system", `Image description:\n${data.image_description}`);
    }
    speakText(data.response || "");
  } catch (error) {
    messages.lastChild.remove();
    addMessage("error", `Image request failed: ${error.message}`);
  }
}

function speakText(text) {
  if (!speechSupported || !ttsEnabled) return;
  if (!text.trim()) return;
  const utterance = new SpeechSynthesisUtterance(text.replace(/\s+/g, " ").trim());
  utterance.lang = getLanguageCode(getSelectedLearningLanguage());
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

async function startCameraCapture() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    cameraPreview.srcObject = cameraStream;
    cameraPanel.classList.remove("hidden");
  } catch (error) {
    addMessage("error", `Camera access failed: ${error.message}`);
  }
}

function stopCameraCapture() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  cameraPanel.classList.add("hidden");
}

function captureCameraImage() {
  const canvas = document.createElement("canvas");
  canvas.width = cameraPreview.videoWidth;
  canvas.height = cameraPreview.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(cameraPreview, 0, 0);
  canvas.toBlob((blob) => {
    capturedImageBlob = blob;
    addMessage("user", "[Image captured from camera]");
    stopCameraCapture();
  }, "image/jpeg");
}

async function sendPrompt(prompt) {
  sendButton.disabled = true;
  addMessage("user", prompt);
  addMessage("system", "Thinking...");

  try {
    const response = await fetch("/ai-chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        prompt,
        language: getSelectedLearningLanguage(),
        profile: {
          grade: localStorage.getItem("tutorbot_grade") || "Grade 9",
          subject: localStorage.getItem("tutorbot_subject") || "General",
        },
      }),
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
  if (promptInput.value.trim()) {
    renderSuggestions(promptInput.value);
  } else {
    suggestions.innerHTML = "";
  }
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file && file.type.startsWith("image/")) {
    addMessage("user", `[Image selected: ${file.name}]`);
    closeUploadMenu();
  }
});

filesInput.addEventListener("change", async (event) => {
  const files = event.target.files;
  if (files.length > 0) {
    addMessage("system", `Uploading ${files.length} file(s)...`);
    for (let file of files) {
      const formData = new FormData();
      formData.append("file", file);
      try {
        const response = await fetch("/files", {
          method: "POST",
          body: formData
        });
        const data = await response.json();
        if (data.filename) {
          addMessage("system", `✅ Uploaded: ${data.filename}`);
        }
      } catch (error) {
        addMessage("error", `Upload failed: ${error.message}`);
      }
    }
    filesInput.value = "";
  }
});

// Upload menu toggle
uploadMenuButton.addEventListener("click", (event) => {
  event.stopPropagation();
  uploadMenu.classList.toggle("hidden");
  uploadMenuButton.classList.toggle("active");
});

// Close menu when clicking outside
document.addEventListener("click", (event) => {
  if (!uploadMenu.contains(event.target) && event.target !== uploadMenuButton) {
    uploadMenu.classList.add("hidden");
    uploadMenuButton.classList.remove("active");
  }
});

function closeUploadMenu() {
  uploadMenu.classList.add("hidden");
  uploadMenuButton.classList.remove("active");
}

// Menu item listeners
menuUploadImage.addEventListener("click", () => {
  fileInput.click();
  closeUploadMenu();
});

menuUseCamera.addEventListener("click", () => {
  startCameraCapture();
  closeUploadMenu();
});

menuProcessImage.addEventListener("click", () => {
  processSelectedImage();
  closeUploadMenu();
});

menuFiles.addEventListener("click", () => {
  filesInput.click();
  closeUploadMenu();
});

captureButton.addEventListener("click", captureCameraImage);
cancelCameraButton.addEventListener("click", () => {
  stopCameraCapture();
  addMessage("system", "Camera capture cancelled.");
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
clearButton.addEventListener("click", async () => {
  try {
    await fetch("/clear", {method: "POST"});
    messages.innerHTML = "";
    addMessage("system", "Conversation cleared.");
  } catch {
    addMessage("error", "Unable to clear chat on the server.");
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

function showFocusModal(requireSelection = false) {
  focusModal.classList.remove("hidden");
  focusModal.setAttribute("aria-hidden", "false");
  if (requireSelection) {
    focusModal.querySelector("button[type=button]").focus();
  }
}

function hideFocusModal() {
  focusModal.classList.add("hidden");
  focusModal.setAttribute("aria-hidden", "true");
}

function updateProfileBanner() {
  const grade = localStorage.getItem("tutorbot_grade") || "Grade 9";
  const subject = localStorage.getItem("tutorbot_subject") || "General";
  if (profileText) {
    profileText.textContent = `${grade} • ${subject}`;
  }
}

function loadProfileFocus() {
  const grade = localStorage.getItem("tutorbot_grade") || "Grade 9";
  const subject = localStorage.getItem("tutorbot_subject") || "General";
  if (gradeSelect) gradeSelect.value = grade;
  if (subjectSelect) subjectSelect.value = subject;
  updateProfileBanner();
}

function saveProfileFocus() {
  const grade = gradeSelect?.value || "Grade 9";
  const subject = subjectSelect?.value || "General";
  localStorage.setItem("tutorbot_grade", grade);
  localStorage.setItem("tutorbot_subject", subject);
  updateProfileBanner();
}

settingsButton.addEventListener("click", async () => {
  openSettings();
  try {
    const response = await fetch("/esp32/settings");
    const data = await response.json();
    ssidInput.value = data.ssid || "";
    passwordInput.value = "";
    loadLanguageSelection();
    updateSpeechRecognitionLanguage();
  } catch {
    addMessage("error", "Could not load ESP32 settings.");
  }
});

closeSettings.addEventListener("click", hideSettings);

changeFocusButton.addEventListener("click", () => showFocusModal());
closeFocusModal.addEventListener("click", hideFocusModal);
saveFocusButton.addEventListener("click", () => {
  saveProfileFocus();
  hideFocusModal();
  addMessage("system", "Learning profile updated.");
});

saveSettings.addEventListener("click", async () => {
  const ssid = ssidInput.value.trim();
  const password = passwordInput.value;
  const selectedInterfaceLanguage = getSelectedInterfaceLanguage();
  const selectedLearningLanguage = getSelectedLearningLanguage();
  localStorage.setItem("tutorbot_interface_language", selectedInterfaceLanguage);
  localStorage.setItem("tutorbot_learning_language", selectedLearningLanguage);
  updateSpeechRecognitionLanguage();

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

loadLanguageSelection();
loadProfileFocus();
if (!localStorage.getItem("tutorbot_grade") || !localStorage.getItem("tutorbot_subject")) {
  showFocusModal(true);
  addMessage("system", "Welcome to TutorBot. Please set your grade and subject focus first.");
} else {
  addMessage("system", "Welcome to TutorBot. Ask a question or use /help.");
}
loadStatus();
loadCommands();

// Check connection status every 2 seconds
setInterval(loadStatus, 2000);

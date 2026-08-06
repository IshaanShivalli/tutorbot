const authOverlay = document.getElementById("authOverlay");
const authForm = document.getElementById("authForm");
const authUsername = document.getElementById("authUsername");
const authPassword = document.getElementById("authPassword");
const authSubmitButton = document.getElementById("authSubmitButton");
const authSubtitle = document.getElementById("authSubtitle");
const authToggleText = document.getElementById("authToggleText");
const authToggleButton = document.getElementById("authToggleButton");
const passwordLabel = document.getElementById("passwordLabel");
const otpLabel = document.getElementById("otpLabel");
const authOtp = document.getElementById("authOtp");

const teacherButton = document.getElementById("teacherButton");
const teacherPanel = document.getElementById("teacherPanel");
const closeTeacher = document.getElementById("closeTeacher");
const btnCreateSplitQuiz = document.getElementById("btnCreateSplitQuiz");
const teacherQuizCount = document.getElementById("teacherQuizCount");
const teacherPassingRate = document.getElementById("teacherPassingRate");

const messagesEl = document.getElementById("messages");
const emptyState = document.getElementById("emptyState");
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("promptInput");
const sendButton = document.getElementById("sendButton");
const statusEl = document.getElementById("status");
const suggestionsEl = document.getElementById("suggestions");

const uploadMenuButton = document.getElementById("uploadMenuButton");
const uploadMenu = document.getElementById("uploadMenu");
const menuUploadImage = document.getElementById("menuUploadImage");
const menuUseCamera = document.getElementById("menuUseCamera");
const menuProcessImage = document.getElementById("menuProcessImage");
const menuFiles = document.getElementById("menuFiles");
const fileInput = document.getElementById("fileInput");
const filesInput = document.getElementById("filesInput");

const cameraPanel = document.getElementById("cameraPanel");
const cameraPreview = document.getElementById("cameraPreview");
const captureButton = document.getElementById("captureButton");
const cancelCameraButton = document.getElementById("cancelCameraButton");

const voiceButton = document.getElementById("voiceButton");
const ttsButton = document.getElementById("ttsButton");
const clearButton = document.getElementById("clearButton");
const settingsButton = document.getElementById("settingsButton");
const settingsPanel = document.getElementById("settingsPanel");
const closeSettings = document.getElementById("closeSettings");
const saveSettings = document.getElementById("saveSettings");
const ssidInput = document.getElementById("ssidInput");
const passwordInput = document.getElementById("passwordInput");
const languageSelect = document.getElementById("languageSelect");
const learningLanguageSelect = document.getElementById("learningLanguageSelect");

const changeFocusButton = document.getElementById("changeFocusButton");
const focusModal = document.getElementById("focusModal");
const closeFocusModal = document.getElementById("closeFocusModal");
const saveFocusButton = document.getElementById("saveFocusButton");
const gradeSelect = document.getElementById("gradeSelect");
const subjectSelect = document.getElementById("subjectSelect");
const profileText = document.getElementById("profileText");

const filesPanel = document.getElementById("filesPanel");
const closeFiles = document.getElementById("closeFiles");
const filesList = document.getElementById("filesList");

let ttsEnabled = false;
let mediaStream = null;
let profile = loadJSON("tb_profile", { grade: "Grade 9", subject: "General" });
let settings = loadJSON("tb_settings", { language: "English", learningLanguage: "English", ssid: "", password: "" });

let isRegistered = false; // Toggles between login and registration mode

// Check session
if (localStorage.getItem("tb_session") === "active") {
  if (authOverlay) authOverlay.classList.add("hidden");
}

if (authToggleButton) {
  authToggleButton.addEventListener("click", () => {
    isRegistered = !isRegistered;
    otpLabel.classList.add("hidden");
    passwordLabel.classList.remove("hidden");
    authOtp.removeAttribute("required");
    if (isRegistered) {
      authSubtitle.textContent = "Create an account to save your learning configurations.";
      authSubmitButton.textContent = "Sign Up";
      authToggleText.textContent = "Already have an account?";
      authToggleButton.textContent = "Log In";
    } else {
      authSubtitle.textContent = "Log in to sync your grades, quizzes, and chat history.";
      authSubmitButton.textContent = "Log In";
      authToggleText.textContent = "New to TutorBot?";
      authToggleButton.textContent = "Create Account";
    }
  });
}

if (authForm) {
  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const user = authUsername.value.trim();
    const pass = authPassword.value.trim();
    
    if (otpLabel.classList.contains("hidden")) {
      authSubmitButton.disabled = true;
      authSubmitButton.textContent = "Sending Code...";
      try {
        const res = await fetch("/api/send-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: user }),
        });
        const data = await res.json();
        authSubmitButton.disabled = false;
        if (data.ok) {
          otpLabel.classList.remove("hidden");
          passwordLabel.classList.add("hidden");
          authOtp.setAttribute("required", "true");
          authSubtitle.textContent = "An OTP code has been sent to your Gmail inbox.";
          authSubmitButton.textContent = "Verify & Login";
        } else {
          alert("Error: " + (data.error || "Failed to send code."));
          authSubmitButton.textContent = isRegistered ? "Sign Up" : "Log In";
        }
      } catch (err) {
        authSubmitButton.disabled = false;
        authSubmitButton.textContent = isRegistered ? "Sign Up" : "Log In";
        alert("Connection error: " + err.message);
      }
    } else {
      const code = authOtp.value.trim();
      authSubmitButton.disabled = true;
      authSubmitButton.textContent = "Verifying...";
      try {
        const res = await fetch("/api/verify-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: user, code: code }),
        });
        const data = await res.json();
        authSubmitButton.disabled = false;
        if (data.ok) {
          localStorage.setItem("tb_session", "active");
          localStorage.setItem("tb_username", user);
          if (authOverlay) authOverlay.classList.add("hidden");
          addMessage("system", `Authenticated successfully via Gmail SMTP OTP as ${user}.`);
        } else {
          alert("Error: " + (data.error || "Invalid OTP code."));
          authSubmitButton.textContent = "Verify & Login";
        }
      } catch (err) {
        authSubmitButton.disabled = false;
        authSubmitButton.textContent = "Verify & Login";
        alert("Connection error: " + err.message);
      }
    }
  });
}

// Teacher Studio Controllers
if (teacherButton) {
  teacherButton.addEventListener("click", () => {
    teacherPanel.classList.remove("hidden");
    teacherPanel.setAttribute("aria-hidden", "false");
  });
}
if (closeTeacher) {
  closeTeacher.addEventListener("click", () => {
    teacherPanel.classList.add("hidden");
    teacherPanel.setAttribute("aria-hidden", "true");
  });
}
if (btnCreateSplitQuiz) {
  btnCreateSplitQuiz.addEventListener("click", () => {
    const qCount = teacherQuizCount.value;
    teacherPanel.classList.add("hidden");
    teacherPanel.setAttribute("aria-hidden", "true");
    const topic = profile.subject || "General";
    sendPrompt(`/quiz ${topic} count=${qCount}`);
  });
}

function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}
function saveJSON(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

function escapeHTML(str) {
  return str.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderInline(text) {
  let html = escapeHTML(text);
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre>${code}</pre>`);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/(https?:\/\/[^\s)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  return html;
}

function hideEmptyState() {
  if (emptyState) emptyState.style.display = "none";
}

function addMessage(role, text, files) {
  hideEmptyState();
  const row = document.createElement("div");
  row.className = `msg-row ${role === "user" ? "user" : ""}`;

  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.innerHTML = renderInline(text || "");

  if (files && files.length) {
    files.forEach((f) => {
      const chip = document.createElement("div");
      chip.className = "file-chip";
      chip.innerHTML = `<span>📄</span><a href="${f.download_url}" target="_blank" rel="noopener">${escapeHTML(f.name)}</a>`;
      bubble.appendChild(chip);
    });
  }

  row.appendChild(bubble);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  if (role === "assistant" && ttsEnabled && text) {
    speak(text);
  }
  return bubble;
}

function addTyping() {
  hideEmptyState();
  const row = document.createElement("div");
  row.className = "msg-row";
  row.id = "typingRow";
  row.innerHTML = `<div class="bubble assistant"><div class="typing"><span></span><span></span><span></span></div></div>`;
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
function removeTyping() {
  const row = document.getElementById("typingRow");
  if (row) row.remove();
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text.replace(/```[\s\S]*?```/g, ""));
  window.speechSynthesis.speak(utter);
}

async function sendPrompt(text) {
  if (!text.trim()) return;
  addMessage("user", text);
  promptInput.value = "";
  autoGrow();
  sendButton.disabled = true;
  addTyping();

  try {
    const res = await fetch("/ai-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: text,
        language: settings.learningLanguage,
        profile: { grade: profile.grade, subject: profile.subject },
      }),
    });
    const data = await res.json();
    removeTyping();
    if (data.error) {
      addMessage("error", data.error);
    } else {
      addMessage(data.type || "assistant", data.response, data.files);
    }
  } catch (err) {
    removeTyping();
    addMessage("error", `Connection failed: ${err.message}`);
  } finally {
    sendButton.disabled = false;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendPrompt(promptInput.value);
});

promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendPrompt(promptInput.value);
  }
});

function autoGrow() {
  promptInput.style.height = "auto";
  promptInput.style.height = Math.min(promptInput.scrollHeight, 200) + "px";
}
promptInput.addEventListener("input", autoGrow);

function updateProfileText() {
  profileText.textContent = `${profile.grade} · ${profile.subject}`;
}

function checkHealth() {
  fetch("/health")
    .then((r) => r.json())
    .then((d) => { statusEl.textContent = d.ok ? "online" : "offline"; })
    .catch(() => { statusEl.textContent = "offline"; });
}

function loadSuggestions() {
  fetch("/commands")
    .then((r) => r.json())
    .then((d) => {
      const cmds = (d.commands || []).slice(0, 6);
      if (!cmds.length) return;
      suggestionsEl.innerHTML = "";
      cmds.forEach((c) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "suggestion";
        btn.textContent = c.usage;
        btn.addEventListener("click", () => {
          promptInput.value = c.usage.split(" ")[0] + " ";
          promptInput.focus();
          autoGrow();
        });
        suggestionsEl.appendChild(btn);
      });
      suggestionsEl.classList.remove("hidden");
    })
    .catch(() => {});
}

clearButton.addEventListener("click", async () => {
  await fetch("/clear", { method: "POST" }).catch(() => {});
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyState);
  emptyState.style.display = "";
});

uploadMenuButton.addEventListener("click", (e) => {
  e.stopPropagation();
  uploadMenu.classList.toggle("hidden");
  uploadMenuButton.classList.toggle("active");
});
document.addEventListener("click", () => {
  uploadMenu.classList.add("hidden");
  uploadMenuButton.classList.remove("active");
});

menuUploadImage.addEventListener("click", () => {
  fileInput.removeAttribute("capture");
  fileInput.click();
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) processImage(fileInput.files[0]);
  fileInput.value = "";
});

menuProcessImage.addEventListener("click", () => {
  fileInput.setAttribute("capture", "environment");
  fileInput.click();
});

menuFiles.addEventListener("click", () => openFilesPanel());

menuUseCamera.addEventListener("click", async () => {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    cameraPreview.srcObject = mediaStream;
    cameraPanel.classList.remove("hidden");
  } catch (err) {
    addMessage("error", `Could not access camera: ${err.message}`);
  }
});

cancelCameraButton.addEventListener("click", stopCamera);
function stopCamera() {
  if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
  mediaStream = null;
  cameraPanel.classList.add("hidden");
}

captureButton.addEventListener("click", () => {
  const canvas = document.createElement("canvas");
  canvas.width = cameraPreview.videoWidth;
  canvas.height = cameraPreview.videoHeight;
  canvas.getContext("2d").drawImage(cameraPreview, 0, 0);
  canvas.toBlob((blob) => {
    stopCamera();
    if (blob) processImage(new File([blob], "capture.png", { type: "image/png" }));
  }, "image/png");
});

async function processImage(file) {
  addMessage("user", `📷 ${file.name}`);
  addTyping();
  const form = new FormData();
  form.append("image", file);
  form.append("language", settings.learningLanguage);
  form.append("profile", JSON.stringify({ grade: profile.grade, subject: profile.subject }));

  try {
    const res = await fetch("/process-image", { method: "POST", body: form });
    const data = await res.json();
    removeTyping();
    if (data.error) addMessage("error", data.error);
    else addMessage("assistant", data.response);
  } catch (err) {
    removeTyping();
    addMessage("error", `Image processing failed: ${err.message}`);
  }
}

filesInput.addEventListener("change", async () => {
  for (const file of filesInput.files) {
    const form = new FormData();
    form.append("file", file);
    try {
      await fetch("/files", { method: "POST", body: form });
    } catch {}
  }
  filesInput.value = "";
  openFilesPanel();
});

async function openFilesPanel() {
  filesPanel.classList.remove("hidden");
  filesPanel.setAttribute("aria-hidden", "false");
  filesList.innerHTML = '<li class="empty">Loading…</li>';
  try {
    const res = await fetch("/files");
    const data = await res.json();
    const files = data.files || [];
    if (!files.length) {
      filesList.innerHTML = '<li class="empty">No files uploaded yet</li>';
      return;
    }
    filesList.innerHTML = "";
    files.forEach((f) => {
      const li = document.createElement("li");
      li.innerHTML = `<a href="${f.download_url}" target="_blank" rel="noopener">${escapeHTML(f.name)}</a><span class="file-size">${(f.size / 1024).toFixed(1)} KB</span>`;
      filesList.appendChild(li);
    });
  } catch {
    filesList.innerHTML = '<li class="empty">Could not load files</li>';
  }
}
closeFiles.addEventListener("click", () => {
  filesPanel.classList.add("hidden");
  filesPanel.setAttribute("aria-hidden", "true");
});

let recognizer = null;
voiceButton.addEventListener("click", () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    addMessage("error", "Voice input is not supported in this browser.");
    return;
  }
  if (recognizer) {
    recognizer.stop();
    return;
  }
  recognizer = new SR();
  recognizer.lang = "en-US";
  recognizer.interimResults = false;
  voiceButton.classList.add("listening");
  recognizer.onresult = (e) => {
    const text = e.results[0][0].transcript;
    promptInput.value = text;
    autoGrow();
  };
  recognizer.onend = () => {
    voiceButton.classList.remove("listening");
    recognizer = null;
  };
  recognizer.start();
});

ttsButton.addEventListener("click", () => {
  ttsEnabled = !ttsEnabled;
  ttsButton.classList.toggle("active", ttsEnabled);
  if (!ttsEnabled) window.speechSynthesis?.cancel();
});

settingsButton.addEventListener("click", () => {
  ssidInput.value = settings.ssid || "";
  passwordInput.value = "";
  languageSelect.value = settings.language;
  learningLanguageSelect.value = settings.learningLanguage;
  settingsPanel.classList.add("open");
  settingsPanel.setAttribute("aria-hidden", "false");
});
closeSettings.addEventListener("click", () => {
  settingsPanel.classList.remove("open");
  settingsPanel.setAttribute("aria-hidden", "true");
});
saveSettings.addEventListener("click", async () => {
  settings.language = languageSelect.value;
  settings.learningLanguage = learningLanguageSelect.value;
  settings.ssid = ssidInput.value.trim();
  settings.password = passwordInput.value;
  saveJSON("tb_settings", settings);

  if (settings.ssid) {
    try {
      await fetch("/esp32/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ssid: settings.ssid, password: settings.password }),
      });
    } catch {}
  }
  settingsPanel.classList.remove("open");
  settingsPanel.setAttribute("aria-hidden", "true");
});

changeFocusButton.addEventListener("click", () => {
  gradeSelect.value = profile.grade;
  subjectSelect.value = profile.subject;
  focusModal.classList.remove("hidden");
  focusModal.setAttribute("aria-hidden", "false");
});
closeFocusModal.addEventListener("click", () => {
  focusModal.classList.add("hidden");
  focusModal.setAttribute("aria-hidden", "true");
});
saveFocusButton.addEventListener("click", () => {
  profile.grade = gradeSelect.value;
  profile.subject = subjectSelect.value;
  saveJSON("tb_profile", profile);
  updateProfileText();
  focusModal.classList.add("hidden");
  focusModal.setAttribute("aria-hidden", "true");
});

updateProfileText();
checkHealth();
loadSuggestions();
setInterval(checkHealth, 30000);
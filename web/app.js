const authOverlay = document.getElementById("authOverlay");
const authForm = document.getElementById("authForm");
const authUsername = document.getElementById("authUsername");
const authEmail = document.getElementById("authEmail");
const authPassword = document.getElementById("authPassword");
const authConfirmPassword = document.getElementById("authConfirmPassword");
const authSubmitButton = document.getElementById("authSubmitButton");
const authSubtitle = document.getElementById("authSubtitle");
const authToggleText = document.getElementById("authToggleText");
const authToggleButton = document.getElementById("authToggleButton");
const passwordLabel = document.getElementById("passwordLabel");
const confirmPasswordLabel = document.getElementById("confirmPasswordLabel");
const emailLabel = document.getElementById("emailLabel");
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
const chatHistoryList = document.getElementById("chatHistoryList");
const newChatButton = document.getElementById("newChatButton");
const historySidebar = document.getElementById("historySidebar");
const sidebarToggleButton = document.getElementById("sidebarToggleButton");
const sidebarBackdrop = document.getElementById("sidebarBackdrop");

function openSidebar() {
  if (historySidebar) historySidebar.classList.add("open");
  if (sidebarBackdrop) sidebarBackdrop.classList.remove("hidden");
}
function closeSidebar() {
  if (historySidebar) historySidebar.classList.remove("open");
  if (sidebarBackdrop) sidebarBackdrop.classList.add("hidden");
}
if (sidebarToggleButton) {
  sidebarToggleButton.addEventListener("click", () => {
    if (historySidebar && historySidebar.classList.contains("open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });
}
if (sidebarBackdrop) {
  sidebarBackdrop.addEventListener("click", closeSidebar);
}
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("promptInput");
const sendButton = document.getElementById("sendButton");
const stopButton = document.getElementById("stopButton");
const statusEl = document.getElementById("status");
const suggestionsEl = document.getElementById("suggestions");

const uploadMenuButton = document.getElementById("uploadMenuButton");
const uploadMenu = document.getElementById("uploadMenu");
const menuUploadImage = document.getElementById("menuUploadImage");
const menuUseCamera = document.getElementById("menuUseCamera");
const menuProcessImage = document.getElementById("menuProcessImage");
const menuFiles = document.getElementById("menuFiles");
const menuReaderMode = document.getElementById("menuReaderMode");
const fileInput = document.getElementById("fileInput");
const filesInput = document.getElementById("filesInput");
const readerInput = document.getElementById("readerInput");

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
const logoutButton = document.getElementById("logoutButton");
const ssidInput = document.getElementById("ssidInput");
const passwordInput = document.getElementById("passwordInput");
const accountUsernameInput = document.getElementById("accountUsername");
const accountEmailInput = document.getElementById("accountEmail");
const accountCurrentPasswordInput = document.getElementById("accountCurrentPassword");
const accountNewPasswordInput = document.getElementById("accountNewPassword");
const accountNewPasswordConfirmInput = document.getElementById("accountNewPasswordConfirm");
const languageSelect = document.getElementById("languageSelect");
const learningLanguageSelect = document.getElementById("learningLanguageSelect");
const surveyQuestionsInput = document.getElementById("surveyQuestionsInput");

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

const readerModal = document.getElementById("readerModal");
const closeReaderModal = document.getElementById("closeReaderModal");
const readerPickFileButton = document.getElementById("readerPickFileButton");
const readerStatus = document.getElementById("readerStatus");

const API_HOST = (window.location.protocol === "file:" || window.location.protocol === "null:") ? "http://127.0.0.1:5000" : window.location.origin;

// ESP32_HOST is used specifically for routes that must be relayed through the
// ESP32 board itself (so its TFT face/LED animate) rather than the PC server
// directly. Falls back to same-origin if no config was injected via api-config.js.
const ESP32_HOST = (window.__TUTORBOT_CONFIG__ && window.__TUTORBOT_CONFIG__.esp32Host)
  ? window.__TUTORBOT_CONFIG__.esp32Host
  : window.location.origin;

let ttsEnabled = false;
let mediaStream = null;
let profile = loadJSON("tb_profile", { grade: "Grade 9", subject: "General" });
let settings = loadJSON("tb_settings", { language: "English", learningLanguage: "English", ssid: "", password: "", theme: "light" });
let surveyQuestions = [];
let activeChatId = localStorage.getItem(`tb_active_chat_${currentAccount()}`) || "";

function currentAccount() {
  const session = localStorage.getItem("tb_session");
  const username = (localStorage.getItem("tb_username") || "").trim().toLowerCase();
  return session === "active" && username ? username : "guest";
}

function accountKey(key) {
  return key.startsWith("tb_account_") ? key : `tb_account_${currentAccount()}_${key}`;
}

function setUIEnabled(enabled) {
  const controls = [chatForm, promptInput, sendButton, newChatButton, teacherButton, settingsButton, uploadMenuButton, menuUploadImage, menuUseCamera, menuProcessImage, menuFiles];
  controls.forEach((control) => {
    if (!control) return;
    control.disabled = !enabled;
    if (enabled) {
      control.classList.remove("disabled-input");
    } else {
      control.classList.add("disabled-input");
    }
  });
  if (promptInput) {
    promptInput.placeholder = enabled ? "Ask TutorBot or type /help" : "Log in to access TutorBot";
  }
  if (!enabled && authOverlay) {
    authOverlay.classList.remove("hidden");
  }
}

function getAccountEmail() {
  return localStorage.getItem(accountKey("tb_email")) || "";
}

function setAccountEmail(email) {
  localStorage.setItem(accountKey("tb_email"), email || "");
}

function getAccountPassword() {
  return loadJSON(accountKey("tb_password"), "");
}

function setAccountPassword(password) {
  saveJSON(accountKey("tb_password"), password || "");
}

function applyTheme(theme) {
  const customControls = document.getElementById("customThemeControls");
  document.body.removeAttribute("style");
  document.body.classList.remove("light-theme");

  if (theme === "light") {
    document.body.classList.add("light-theme");
    if (customControls) customControls.style.display = "none";
  } else if (theme === "dark") {
    if (customControls) customControls.style.display = "none";
  } else if (theme === "custom") {
    if (customControls) customControls.style.display = "block";
    const ct = settings.customTheme || {
      ink: "#0a0812",
      panel: "#1c1830",
      chalk: "#a855f7",
      text: "#f5f2fa"
    };
    document.body.style.setProperty("--ink", ct.ink);
    document.body.style.setProperty("--panel", ct.panel + "cc");
    document.body.style.setProperty("--panel-2", ct.panel);
    document.body.style.setProperty("--chalk", ct.chalk);
    document.body.style.setProperty("--chalk-soft", ct.chalk + "26");
    document.body.style.setProperty("--text", ct.text);
    document.body.style.setProperty("--muted", ct.text + "aa");
    
    document.getElementById("colorInk").value = ct.ink;
    document.getElementById("colorPanel").value = ct.panel;
    document.getElementById("colorChalk").value = ct.chalk;
    document.getElementById("colorText").value = ct.text;
  }

  const themeSelect = document.getElementById("themeSelect");
  if (themeSelect) {
    themeSelect.value = theme;
  }
}
applyTheme(settings.theme || "light");

let isRegistered = false; // Toggles between login and registration mode

// Check session
if (localStorage.getItem("tb_session") === "active") {
  if (authOverlay) authOverlay.classList.add("hidden");
  setUIEnabled(true);
} else {
  setUIEnabled(false);
}

if (authToggleButton) {
  authToggleButton.addEventListener("click", (e) => {
    e.preventDefault();
    isRegistered = !isRegistered;
    otpLabel.classList.add("hidden");
    passwordLabel.classList.remove("hidden");
    emailLabel.classList.toggle("hidden", !isRegistered);
    confirmPasswordLabel.classList.toggle("hidden", !isRegistered);
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

function askForDisplayNameIfMissing(username) {
  const key = `tb_display_name_${username}`;
  let name = localStorage.getItem(key);
  if (!name) {
    name = (window.prompt("What should we call you?", "") || "").trim();
    if (name) {
      localStorage.setItem(key, name);
    }
  }
  return name;
}

if (authForm) {
  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const user = authUsername.value.trim();
    const email = authEmail.value.trim();
    const identifier = user || email;
    const pass = authPassword.value.trim();
    const confirmPass = authConfirmPassword.value.trim();
    
    if (otpLabel.classList.contains("hidden")) {
      if (isRegistered && (!identifier || !email || pass !== confirmPass)) {
        alert("Please enter a username, a valid email, and matching password confirmation.");
        return;
      }
      if (!isRegistered && !identifier) {
        alert("Please enter your username or email.");
        return;
      }
      authSubmitButton.disabled = true;
      authSubmitButton.textContent = "Sending Code...";
      try {
        const res = await fetch(`${API_HOST}/api/send-otp`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: identifier,
            email: email,
            password: pass,
            confirmPassword: confirmPass,
            mode: isRegistered ? "register" : "login",
          }),
        });
        const data = await parseApiResponse(res);
        authSubmitButton.disabled = false;
        if (res.ok && data.ok) {
          otpLabel.classList.remove("hidden");
          passwordLabel.classList.add("hidden");
          confirmPasswordLabel.classList.add("hidden");
          emailLabel.classList.add("hidden");
          authOtp.setAttribute("required", "true");
          authSubtitle.textContent = "An OTP code has been sent to your email inbox.";
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
        const res = await fetch(`${API_HOST}/api/verify-otp`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: user, code: code, mode: isRegistered ? "registration" : "login" }),
        });
        const data = await parseApiResponse(res);
        authSubmitButton.disabled = false;
        if (res.ok && data.ok) {
          const sessionUser = data.user?.username || user;
          localStorage.setItem("tb_session", "active");
          localStorage.setItem("tb_username", sessionUser);
          setAccountEmail(data.user?.email || email);
          reloadAccountState();
          setUIEnabled(true);
          if (authOverlay) authOverlay.classList.add("hidden");
          const displayName = askForDisplayNameIfMissing(sessionUser);
          addMessage("system", `Hello ${displayName || sessionUser}`);
          maybeShowSurvey();
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
    const raw = localStorage.getItem(accountKey(key)) || localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}
function saveJSON(key, value) {
  try { localStorage.setItem(accountKey(key), JSON.stringify(value)); } catch {}
}

async function parseApiResponse(res) {
  const text = await res.text();
  const contentType = (res.headers.get("content-type") || "").toLowerCase();
  const isJson = contentType.includes("application/json");

  if (isJson) {
    try {
      return JSON.parse(text || "{}");
    } catch {
      return { error: text || `Server returned invalid JSON (${res.status})`, status: res.status };
    }
  }

  if (!res.ok) {
    try {
      return JSON.parse(text || "{}");
    } catch {
      return { error: text || `Server returned ${res.status}`, status: res.status };
    }
  }

  return {};
}

function getChats() {
  return loadJSON("tb_chats", []);
}

function saveChats(chats) {
  saveJSON("tb_chats", chats);
}

function ensureActiveChat() {
  let chats = getChats();
  if (!activeChatId || !chats.some((chat) => chat.id === activeChatId)) {
    const chat = { id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), title: "New chat", messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    chats.unshift(chat);
    activeChatId = chat.id;
    localStorage.setItem(`tb_active_chat_${currentAccount()}`, activeChatId);
    saveChats(chats);
  }
  return getChats().find((chat) => chat.id === activeChatId);
}

function saveMessageToChat(chatId, role, text, files) {
  if (role === "command" || !chatId) return;
  let chats = getChats();
  let chat = chats.find((item) => item.id === chatId);
  if (!chat) {
    return;
  }
  chat.messages.push({ role, text, files: files || [], timestamp: Date.now() });
  if (chat.title === "New chat" && role === "user" && text) {
    chat.title = text.slice(0, 42);
  }
  chat.updatedAt = Date.now();
  saveChats(chats);
  renderChatSidebar();
}

function saveMessageToActiveChat(role, text, files) {
  saveMessageToChat(activeChatId, role, text, files);
}

function renderChatSidebar() {
  if (!chatHistoryList) return;
  const chats = getChats();
  if (!chats.length) {
    chatHistoryList.innerHTML = `<div class="chat-history-empty">No chats yet</div>`;
    return;
  }
  chatHistoryList.innerHTML = "";
  chats.forEach((chat) => {
    const row = document.createElement("div");
    row.className = "chat-history-item";
    const open = document.createElement("button");
    open.type = "button";
    open.className = `chat-history-open ${chat.id === activeChatId ? "active" : ""}`;
    open.textContent = chat.title || "New chat";
    open.addEventListener("click", () => {
      loadChat(chat.id);
      closeSidebar();
    });
    const del = document.createElement("button");
    del.type = "button";
    del.className = "chat-history-delete";
    del.textContent = "×";
    del.title = "Delete chat";
    del.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteChat(chat.id);
    });
    row.append(open, del);
    chatHistoryList.appendChild(row);
  });
}

function loadChat(chatId) {
  const chats = getChats();
  const chat = chats.find((item) => item.id === chatId);
  if (!chat) return;
  activeChatId = chat.id;
  localStorage.setItem(`tb_active_chat_${currentAccount()}`, activeChatId);
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyState);
  emptyState.style.display = "";
  (chat.messages || []).forEach((message) => addMessage(message.role, message.text, message.files, { skipSave: true }));
  renderChatSidebar();
}

function startNewChat() {
  const chats = getChats();
  const chat = { id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), title: "New chat", messages: [], createdAt: Date.now(), updatedAt: Date.now() };
  chats.unshift(chat);
  activeChatId = chat.id;
  localStorage.setItem(`tb_active_chat_${currentAccount()}`, activeChatId);
  saveChats(chats);
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyState);
  emptyState.style.display = "";
  renderChatSidebar();
}

function maybeStartNewChat() {
  const chats = getChats();
  const activeChat = chats.find((item) => item.id === activeChatId);
  if (!activeChat || activeChat.title !== "New chat") {
    startNewChat();
  }
}

function deleteChat(chatId) {
  let chats = getChats().filter((chat) => chat.id !== chatId);
  saveChats(chats);
  if (activeChatId === chatId) {
    activeChatId = chats[0]?.id || "";
    if (activeChatId) loadChat(activeChatId);
    else startNewChat();
  } else {
    renderChatSidebar();
  }
}

function reloadAccountState() {
  profile = loadJSON("tb_profile", { grade: "Grade 9", subject: "General" });
  settings = loadJSON("tb_settings", { language: "English", learningLanguage: "English", ssid: "", password: "", theme: "light" });
  applyTheme(settings.theme || "light");
  updateProfileText();
  checkStreak();
}

function logout() {
  localStorage.removeItem("tb_session");
  localStorage.removeItem("tb_username");
  if (settingsPanel) {
    settingsPanel.classList.add("hidden");
    settingsPanel.setAttribute("aria-hidden", "true");
  }
  setUIEnabled(false);
  reloadAccountState();
  if (accountUsernameInput) accountUsernameInput.value = "";
  if (accountEmailInput) accountEmailInput.value = "";
  if (authForm) authForm.reset();
  if (otpLabel) otpLabel.classList.add("hidden");
  if (passwordLabel) passwordLabel.classList.remove("hidden");
  if (authSubtitle) authSubtitle.textContent = "";
  if (authSubmitButton) authSubmitButton.textContent = isRegistered ? "Sign Up" : "Log In";
  if (authOverlay) authOverlay.classList.remove("hidden");
}

if (logoutButton) {
  logoutButton.addEventListener("click", () => {
    if (confirm("Log out of TutorBot?")) {
      logout();
    }
  });
}

async function saveProfileToServer() {
  const username = currentAccount();
  if (!username || username === "guest" || localStorage.getItem("tb_session") !== "active") return;
  try {
    await fetch(`${API_HOST}/api/user-profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, profile }),
    });
  } catch {}
}

function speechCode(language) {
  const codes = {
    English: "en-US",
    Hindi: "hi-IN",
    Kannada: "kn-IN",
    Tamil: "ta-IN",
    Telugu: "te-IN",
    Malayalam: "ml-IN",
    Marathi: "mr-IN",
    Bengali: "bn-IN",
    Gujarati: "gu-IN",
    Spanish: "es-ES",
    French: "fr-FR",
    German: "de-DE",
    Portuguese: "pt-PT",
    Italian: "it-IT",
    Arabic: "ar-SA",
    Chinese: "zh-CN",
    Japanese: "ja-JP",
    Korean: "ko-KR",
    Russian: "ru-RU",
  };
  return codes[language] || "en-US";
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

function addMessage(role, text, files, options = {}) {
  hideEmptyState();
  const saveChatId = options.chatId || activeChatId;
  if (!options.skipSave) {
    saveLogToHistory(role, text);
    saveMessageToChat(saveChatId, role, text, files);
  }
  if (options.chatId && options.chatId !== activeChatId) {
    return;
  }
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

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar tutorbot-avatar";
    avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4M8 15h.01M16 15h.01"></path></svg>`;
    row.appendChild(avatar);
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

// Reveals `text` word-by-word inside a fresh assistant bubble, to visually
// communicate "generating" even though the backend returns one full response
// rather than a real token stream. Returns a controller with .skip() to
// instantly reveal the rest (used when the user hits Stop) and a promise
// that resolves once the reveal finishes (or is skipped).
function addStreamedMessage(text, options = {}) {
  hideEmptyState();
  const row = document.createElement("div");
  row.className = "msg-row";

  const avatar = document.createElement("div");
  avatar.className = "avatar tutorbot-avatar";
  avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4M8 15h.01M16 15h.01"></path></svg>`;
  row.appendChild(avatar);

  const bubble = document.createElement("div");
  bubble.className = "bubble assistant streaming";
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  const words = (text || "").split(/(\s+)/); // keep whitespace tokens so spacing is preserved
  let i = 0;
  let stopped = false;
  let resolveDone;
  const done = new Promise((resolve) => { resolveDone = resolve; });

  function finish() {
    bubble.classList.remove("streaming");
    bubble.innerHTML = renderInline(text || "");
    resolveDone();
  }

  function tick() {
    if (stopped) return;
    if (i >= words.length) {
      finish();
      return;
    }
    i++;
    bubble.textContent = words.slice(0, i).join("");
    messagesEl.scrollTop = messagesEl.scrollHeight;
    setTimeout(tick, 28);
  }
  tick();

  return {
    skip() {
      stopped = true;
      finish();
    },
    done,
  };
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text.replace(/```[\s\S]*?```/g, ""));
  utter.rate = 0.78;
  utter.pitch = 1;
  window.speechSynthesis.speak(utter);
}

function saveLogToHistory(role, text) {
  try {
    const logs = loadJSON("tb_chat_logs", []);
    logs.push({
      role: role,
      text: text,
      timestamp: new Date().toLocaleTimeString()
    });
    saveJSON("tb_chat_logs", logs.slice(-100));
  } catch (e) {}
}

let activeGenerationController = null;
let activeStreamHandle = null;
let isGenerating = false;

function setGeneratingState(generating) {
  isGenerating = generating;
  sendButton.classList.toggle("hidden", generating);
  if (stopButton) stopButton.classList.toggle("hidden", !generating);
  promptInput.disabled = generating;
}

async function sendPrompt(text) {
  if (isGenerating) return; // one response at a time -- ignore repeat sends while a reply is in flight
  if (currentAccount() === "guest") {
    addMessage("error", "Please log in before using TutorBot.");
    return;
  }
  if (!text.trim()) return;
  const isCommand = text.startsWith("/");
  const requestChatId = activeChatId;
  if (isCommand && text.trim() === "/clear") {
    promptInput.value = "";
    autoGrow();
    clearActiveChat();
    return;
  }
  if (isCommand && /^\/(define|dictionary)\b/i.test(text.trim())) {
    const word = text.trim().replace(/^\/(define|dictionary)\s*/i, "").trim();
    addMessage("user", text, null, { chatId: requestChatId });
    saveLogToHistory("command", text);
    promptInput.value = "";
    autoGrow();
    if (!word) {
      addMessage("system", "Usage: /define <word>", null, { chatId: requestChatId });
      return;
    }
    setGeneratingState(true);
    addTyping();
    try {
      const res = await fetch(`${ESP32_HOST}/dictionary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word, profile: { grade: profile.grade, subject: profile.subject } }),
      });
      const data = await res.json();
      removeTyping();
      if (data.error) {
        addMessage("error", data.error, null, { chatId: requestChatId });
      } else {
        // addMessage() already speaks the text aloud when ttsEnabled, same
        // as any other assistant reply -- no separate TTS wiring needed.
        addMessage("assistant", `**${data.word}**\n\n${data.meaning}`, null, { chatId: requestChatId });
      }
    } catch (err) {
      removeTyping();
      addMessage("error", `Connection failed: ${err.message}`, null, { chatId: requestChatId });
    } finally {
      setGeneratingState(false);
    }
    return;
  }
  addMessage("user", text, null, { chatId: requestChatId });
  if (isCommand) {
    saveLogToHistory("command", text);
    if (text.trim().toLowerCase().startsWith("/spell")) {
      const spellWord = text.trim().slice(6).trim();
      if (spellWord) {
        speakWord(spellWord);
      }
    }
  }
  promptInput.value = "";
  autoGrow();
  sendButton.classList.remove("sent-pulse");
  void sendButton.offsetWidth; // restart animation if fired rapidly
  sendButton.classList.add("sent-pulse");
  setGeneratingState(true);
  addTyping();

  activeGenerationController = new AbortController();

  try {
    const res = await fetch(`${ESP32_HOST}/ai-chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: text,
        language: settings.learningLanguage,
        interfaceLanguage: settings.language,
        profile: { grade: profile.grade, subject: profile.subject },
      }),
      signal: activeGenerationController.signal,
    });
    const data = await res.json();
    removeTyping();
    if (data.error) {
      addMessage("error", data.error, null, { chatId: requestChatId });
    } else {
      if (data.settings && data.settings.learningLanguage) {
        settings.learningLanguage = data.settings.learningLanguage;
        saveJSON("tb_settings", settings);
      }
      if (data.type && data.type !== "assistant") {
        addMessage(data.type, data.response, data.files, { chatId: requestChatId });
      } else {
        // Persist to history/localStorage right away (skipSave:false is the
        // default) but render nothing yet -- addStreamedMessage below handles
        // the on-screen bubble, so we save via a silent call first.
        saveLogToHistory(data.type || "assistant", data.response);
        saveMessageToChat(requestChatId, data.type || "assistant", data.response, data.files);

        activeStreamHandle = addStreamedMessage(data.response, {});
        await activeStreamHandle.done;
        activeStreamHandle = null;

        if (data.files && data.files.length) {
          const lastBubble = messagesEl.lastElementChild?.querySelector(".bubble");
          if (lastBubble) {
            data.files.forEach((f) => {
              const chip = document.createElement("div");
              chip.className = "file-chip";
              chip.innerHTML = `<span>📄</span><a href="${f.download_url}" target="_blank" rel="noopener">${escapeHTML(f.name)}</a>`;
              lastBubble.appendChild(chip);
            });
          }
        }
        if (ttsEnabled && data.response) speak(data.response);
      }
    }
  } catch (err) {
    removeTyping();
    if (err.name === "AbortError") {
      addMessage("system", "Generation stopped.", null, { chatId: requestChatId });
    } else {
      addMessage("error", `Connection failed: ${err.message}`, null, { chatId: requestChatId });
    }
  } finally {
    setGeneratingState(false);
    activeGenerationController = null;
  }
}

if (stopButton) {
  stopButton.addEventListener("click", () => {
    // Previously this only stopped the visual text reveal or the network
    // fetch, never the actual speech -- so on phones (where the fetch often
    // finishes before you tap Stop) the reader kept talking regardless.
    // Cancelling here unconditionally makes Stop behave the same everywhere.
    window.speechSynthesis?.cancel();

    if (activeStreamHandle) {
      // Reveal is running client-side (response already arrived) -- just
      // fast-forward to the full text instead of aborting a finished fetch.
      activeStreamHandle.skip();
      activeStreamHandle = null;
      setGeneratingState(false);
    } else if (activeGenerationController) {
      // Still waiting on the network response -- actually cancel it.
      activeGenerationController.abort();
    }
  });
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

function clearActiveChat() {
  const chats = getChats();
  const chat = chats.find((item) => item.id === activeChatId);
  if (!chat) return;
  chat.messages = [];
  chat.updatedAt = Date.now();
  saveChats(chats);
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyState);
  emptyState.style.display = "";
  renderChatSidebar();
}

clearButton.addEventListener("click", () => {
  clearActiveChat();
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

menuReaderMode.addEventListener("click", () => openReaderModal());

const headerReaderButton = document.getElementById("headerReaderButton");
if (headerReaderButton) {
  headerReaderButton.addEventListener("click", () => openReaderModal());
}

function openReaderModal() {
  readerStatus.textContent = "";
  readerModal.classList.remove("hidden");
  readerModal.setAttribute("aria-hidden", "false");
}

function closeReaderModalFn() {
  readerModal.classList.add("hidden");
  readerModal.setAttribute("aria-hidden", "true");
}

closeReaderModal.addEventListener("click", closeReaderModalFn);

readerPickFileButton.addEventListener("click", () => readerInput.click());

readerInput.addEventListener("change", async () => {
  const file = readerInput.files[0];
  readerInput.value = "";
  if (!file) return;

  const modeChoice = document.querySelector('input[name="readerMode"]:checked');
  const mode = modeChoice ? modeChoice.value : "summarize";

  readerStatus.textContent = `Reading ${file.name}...`;

  const form = new FormData();
  form.append("document", file);
  form.append("language", settings.learningLanguage);
  form.append("mode", mode);
  form.append("profile", JSON.stringify({ grade: profile.grade, subject: profile.subject }));

  try {
    const res = await fetch(`${API_HOST}/read-document`, { method: "POST", body: form });
    const data = await res.json();
    if (data.error) {
      readerStatus.textContent = data.error;
      return;
    }
    closeReaderModalFn();
    addMessage("user", `📖 Reader mode: ${file.name}`);
    addMessage("assistant", data.response);
    if (data.truncated) {
      addMessage("system", "Note: this document was long, so only the first portion was read.");
    }
  } catch (err) {
    readerStatus.textContent = `Reader mode failed: ${err.message}`;
  }
});

menuUseCamera.addEventListener("click", async () => {
  if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    addMessage(
      "error",
      "Camera access needs a secure connection (HTTPS) or 'localhost'. Since you're on " +
      window.location.origin +
      ", your browser is blocking camera access for security reasons. Use \"Upload image\" instead, or ask the site owner to enable HTTPS on the server."
    );
    return;
  }
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
  if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    addMessage("error", "Voice input needs HTTPS on phones. Use localhost on the PC, or host TutorBot with HTTPS for mobile voice.");
    return;
  }
  if (recognizer) {
    recognizer.stop();
    return;
  }
  recognizer = new SR();
  recognizer.lang = speechCode(settings.learningLanguage);
  recognizer.interimResults = false;
  voiceButton.classList.add("listening");
  addMessage("system", `Listening in ${settings.learningLanguage}...`);
  recognizer.onresult = (e) => {
    const text = e.results[0][0].transcript;
    promptInput.value = text;
    autoGrow();
    promptInput.focus();
  };
  recognizer.onerror = (e) => {
    const reason = e.error || "unknown";
    addMessage("error", `Voice input failed: ${reason}. Check microphone permission and browser support.`);
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
  if (currentAccount() === "guest") {
    alert("Please log in before opening settings.");
    return;
  }
  ssidInput.value = settings.ssid || "";
  passwordInput.value = "";
  if (accountUsernameInput) accountUsernameInput.value = currentAccount();
  if (accountEmailInput) accountEmailInput.value = getAccountEmail();
  if (accountCurrentPasswordInput) accountCurrentPasswordInput.value = "";
  if (accountNewPasswordInput) accountNewPasswordInput.value = "";
  if (accountNewPasswordConfirmInput) accountNewPasswordConfirmInput.value = "";
  languageSelect.value = settings.language;
  learningLanguageSelect.value = settings.learningLanguage;
  const themeSelect = document.getElementById("themeSelect");
  if (themeSelect) {
    themeSelect.value = settings.theme || "light";
    document.getElementById("customThemeControls").style.display = (settings.theme === "custom") ? "block" : "none";
  }
  if (surveyQuestionsInput) {
    fetch("/api/survey-questions")
      .then((r) => r.json())
      .then((data) => {
        surveyQuestions = data.questions || [];
        surveyQuestionsInput.value = surveyQuestions.map((q) => q.label || q.key).join("\n");
      })
      .catch(() => {
        surveyQuestionsInput.value = "Grade level\nPreferred subject\nWeakest subject";
      });
  }
  settingsPanel.classList.remove("hidden");
  settingsPanel.classList.add("open");
  settingsPanel.setAttribute("aria-hidden", "false");
});

const themeSelectEl = document.getElementById("themeSelect");
if (themeSelectEl) {
  themeSelectEl.addEventListener("change", (e) => {
    document.getElementById("customThemeControls").style.display = (e.target.value === "custom") ? "block" : "none";
  });
}

closeSettings.addEventListener("click", () => {
  settingsPanel.classList.remove("open");
  settingsPanel.classList.add("hidden");
  settingsPanel.setAttribute("aria-hidden", "true");
});
saveSettings.addEventListener("click", async () => {
  settings.language = languageSelect.value;
  settings.learningLanguage = learningLanguageSelect.value;
  settings.ssid = ssidInput.value.trim();
  settings.password = passwordInput.value;
  const themeSelect = document.getElementById("themeSelect");
  if (themeSelect) {
    settings.theme = themeSelect.value;
    if (settings.theme === "custom") {
      settings.customTheme = {
        ink: document.getElementById("colorInk").value,
        panel: document.getElementById("colorPanel").value,
        chalk: document.getElementById("colorChalk").value,
        text: document.getElementById("colorText").value
      };
    }
    applyTheme(settings.theme);
  }
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
  if (surveyQuestionsInput) {
    const questions = surveyQuestionsInput.value
      .split(/\r?\n/)
      .map((line, index) => line.trim())
      .filter(Boolean)
      .map((label, index) => ({
        key: index === 0 ? "grade" : index === 1 ? "subject" : index === 2 ? "weak_subject" : `question_${index + 1}`,
        label,
        type: index < 2 ? "select" : "text",
      }));
    if (questions.length) {
      try {
        await fetch("/api/survey-questions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ questions }),
        });
        surveyQuestions = questions;
      } catch {}
    }
  }
  settingsPanel.classList.remove("open");
  settingsPanel.classList.add("hidden");
  settingsPanel.setAttribute("aria-hidden", "true");
  addMessage("system", `Settings saved. TutorBot will respond in ${settings.learningLanguage}.`);
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
  saveProfileToServer();
  updateProfileText();
  focusModal.classList.add("hidden");
  focusModal.setAttribute("aria-hidden", "true");
});

// Theme quick toggle button
const themeToggleButton = document.getElementById("themeToggleButton");
if (themeToggleButton) {
  themeToggleButton.addEventListener("click", () => {
    const currentTheme = settings.theme || "light";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    settings.theme = nextTheme;
    applyTheme(nextTheme);
    saveJSON("tb_settings", settings);
  });
}

// Persistent command buttons
function initCommandButtons() {
  const buttons = document.querySelectorAll(".cmd-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      const cmd = btn.getAttribute("data-cmd");
      if (cmd === "/quiz" || cmd === "/search" || cmd === "/doc" || cmd === "/define") {
        promptInput.value = cmd + " ";
        promptInput.focus();
        autoGrow();
      } else {
        sendPrompt(cmd);
      }
    });
  });
}

// Spell Practice modal handlers
const spellButton = document.getElementById("spellButton");
const spellModal = document.getElementById("spellModal");
const closeSpellModal = document.getElementById("closeSpellModal");
const spellHearBtn = document.getElementById("spellHearBtn");
const spellInput = document.getElementById("spellInput");
const spellFeedback = document.getElementById("spellFeedback");
const spellCheckBtn = document.getElementById("spellCheckBtn");
const spellNextBtn = document.getElementById("spellNextBtn");
const spellScoreEl = document.getElementById("spellScore");
const spellStreakEl = document.getElementById("spellStreak");

let currentSpellWord = "";
let spellScore = 0;
let spellStreak = 0;

const spellWordLists = {
  "Grade 6": ["abandon", "behavior", "chronology", "dialogue", "endeavor", "fantastic", "geometry", "horizon", "influence", "journey"],
  "Grade 7": ["accommodation", "beneficial", "characteristic", "differentiate", "enthusiasm", "fluctuation", "gullible", "hypocrisy", "impartial", "judicious"],
  "Grade 8": ["achievement", "belligerent", "conspicuous", "deteriorate", "exaggerate", "formidable", "garrulous", "hypothesis", "inadvertent", "juxtaposition"],
  "Grade 9": ["aesthetic", "benevolent", "cacophony", "deference", "ephemeral", "fortuitous", "gregarious", "hyperbole", "impetuous", "loquacious"],
  "Grade 10": ["acquiesce", "capricious", "dichotomy", "equivocal", "fastidious", "harangue", "idiosyncrasy", "laconic", "obfuscate", "pragmatic"],
  "Grade 11": ["anachronism", "camaraderie", "deleterious", "ephemeral", "facetious", "grandiloquent", "impetuous", "mendacious", "nefarious", "parsimonious"],
  "Grade 12": ["cacophony", "chicanery", "desultory", "egregious", "fecund", "garrulous", "insidious", "mellifluous", "obsequious", "querulous"],
  "College": ["anathema", "bilious", "crepuscular", "diaphanous", "exculpate", "hegemony", "inimical", "hubris", "paradigmatic", "surreptitious"],
  "Adult": ["absquatulate", "bourgeoisie", "floccinaucinihilipilification", "honorificabilitudinitatibus", "sesquipedalian", "supercalifragilisticexpialidocious", "tergiversation"]
};

function speakWord(word) {
  const spokenWord = String(word || "").trim();
  if (!spokenWord || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(spokenWord);
  utter.lang = "en-US";
  utter.rate = 0.65;
  utter.pitch = 1;
  window.speechSynthesis.speak(utter);
}

function getNextSpellWord() {
  const grade = profile.grade || "Grade 9";
  const list = spellWordLists[grade] || spellWordLists["Grade 9"];
  const randomWord = list[Math.floor(Math.random() * list.length)];
  currentSpellWord = randomWord;
  spellInput.value = "";
  spellFeedback.className = "spell-feedback";
  spellFeedback.textContent = "";
  spellNextBtn.classList.add("hidden");
  spellCheckBtn.classList.remove("hidden");
  speakWord(currentSpellWord);
}

if (spellButton && spellModal) {
  spellButton.addEventListener("click", () => {
    spellModal.classList.remove("hidden");
    spellModal.setAttribute("aria-hidden", "false");
    getNextSpellWord();
  });

  closeSpellModal.addEventListener("click", () => {
    spellModal.classList.add("hidden");
    spellModal.setAttribute("aria-hidden", "true");
    window.speechSynthesis?.cancel();
  });

  spellHearBtn.addEventListener("click", () => {
    speakWord(spellInput.value || currentSpellWord);
  });

  spellInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      speakWord(spellInput.value || currentSpellWord);
    }
  });

  spellCheckBtn.addEventListener("click", () => {
    const userAns = spellInput.value.trim().toLowerCase();
    if (!userAns) return;
    if (userAns === currentSpellWord.toLowerCase()) {
      spellScore += 10;
      spellStreak += 1;
      spellFeedback.textContent = "✓ Correct! Well done!";
      spellFeedback.className = "spell-feedback correct";
      spellCheckBtn.classList.add("hidden");
      spellNextBtn.classList.remove("hidden");
    } else {
      spellStreak = 0;
      spellFeedback.textContent = `✗ Incorrect. The correct spelling is "${currentSpellWord}".`;
      spellFeedback.className = "spell-feedback incorrect";
      spellCheckBtn.classList.add("hidden");
      spellNextBtn.classList.remove("hidden");
    }
    spellScoreEl.textContent = spellScore;
    spellStreakEl.textContent = spellStreak;
    
    // Save to profile
    profile.spellScore = spellScore;
    if (spellStreak > (profile.longestStreak || 0)) {
      profile.longestStreak = spellStreak;
    }
    saveJSON("tb_profile", profile);
    saveProfileToServer();
  });

  spellNextBtn.addEventListener("click", () => {
    getNextSpellWord();
    spellInput.focus();
  });
}

// Dictation Mode handlers
const dictateButton = document.getElementById("dictateButton");
const dictationModal = document.getElementById("dictationModal");
const closeDictationModal = document.getElementById("closeDictationModal");
const dictationHearBtn = document.getElementById("dictationHearBtn");
const dictationInput = document.getElementById("dictationInput");
const dictationFeedback = document.getElementById("dictationFeedback");
const dictationStartBtn = document.getElementById("dictationStartBtn");
const dictationNextBtn = document.getElementById("dictationNextBtn");
const dictationTimerEl = document.getElementById("dictationTimer");
const dictationStreakEl = document.getElementById("dictationStreak");

let dictationTimer = 10;
let dictationInterval = null;
let dictationStreak = 0;
let currentDictationWord = "";

function startDictationTimer() {
  clearInterval(dictationInterval);
  dictationTimer = 10;
  dictationTimerEl.textContent = dictationTimer + "s";
  dictationInterval = setInterval(() => {
    dictationTimer--;
    dictationTimerEl.textContent = dictationTimer + "s";
    if (dictationTimer <= 0) {
      clearInterval(dictationInterval);
      dictationStreak = 0;
      dictationStreakEl.textContent = dictationStreak;
      dictationFeedback.textContent = `✗ Time's Up! The word was "${currentDictationWord}".`;
      dictationFeedback.className = "spell-feedback incorrect";
      dictationStartBtn.classList.add("hidden");
      dictationNextBtn.classList.remove("hidden");
    }
  }, 1000);
}

function nextDictationWord() {
  const grade = profile.grade || "Grade 9";
  const list = spellWordLists[grade] || spellWordLists["Grade 9"];
  currentDictationWord = list[Math.floor(Math.random() * list.length)];
  dictationInput.value = "";
  dictationFeedback.textContent = "";
  dictationFeedback.className = "spell-feedback";
  dictationNextBtn.classList.add("hidden");
  dictationStartBtn.classList.remove("hidden");
  dictationStartBtn.textContent = "Check Spelling";
  speakWord(currentDictationWord);
  startDictationTimer();
}

if (dictateButton && dictationModal) {
  dictateButton.addEventListener("click", () => {
    dictationModal.classList.remove("hidden");
    dictationModal.setAttribute("aria-hidden", "false");
    nextDictationWord();
  });
  
  closeDictationModal.addEventListener("click", () => {
    dictationModal.classList.add("hidden");
    dictationModal.setAttribute("aria-hidden", "true");
    clearInterval(dictationInterval);
    window.speechSynthesis?.cancel();
  });
  
  dictationHearBtn.addEventListener("click", () => {
    speakWord(currentDictationWord);
  });
  
  dictationStartBtn.addEventListener("click", () => {
    if (dictationStartBtn.textContent === "Start Session") {
      nextDictationWord();
      return;
    }
    const val = dictationInput.value.trim().toLowerCase();
    if (!val) return;
    clearInterval(dictationInterval);
    if (val === currentDictationWord.toLowerCase()) {
      dictationStreak++;
      dictationFeedback.textContent = "✓ Correct spelling!";
      dictationFeedback.className = "spell-feedback correct";
    } else {
      dictationStreak = 0;
      dictationFeedback.textContent = `✗ Incorrect. It is "${currentDictationWord}".`;
      dictationFeedback.className = "spell-feedback incorrect";
    }
    dictationStreakEl.textContent = dictationStreak;
    if (dictationStreak > (profile.longestStreak || 0)) {
      profile.longestStreak = dictationStreak;
      saveJSON("tb_profile", profile);
      saveProfileToServer();
    }
    dictationStartBtn.classList.add("hidden");
    dictationNextBtn.classList.remove("hidden");
  });
  
  dictationNextBtn.addEventListener("click", () => {
    nextDictationWord();
    dictationInput.focus();
  });
}

// Survey System
const surveyModal = document.getElementById("surveyModal");
const submitSurvey = document.getElementById("submitSurvey");
function maybeShowSurvey() {
  if (surveyModal && !profile.surveyFilled) {
    fetch("/api/survey-questions")
      .then((r) => r.json())
      .then((data) => {
        const questions = data.questions || [];
        const labels = surveyModal.querySelectorAll(".field-label");
        questions.slice(0, 3).forEach((q, index) => {
          const field = labels[index];
          if (field && q.label) {
            const control = field.querySelector("input, select");
            field.firstChild.textContent = q.label;
            if (control && !field.contains(control)) field.appendChild(control);
          }
        });
      })
      .catch(() => {});
    surveyModal.classList.remove("hidden");
    surveyModal.setAttribute("aria-hidden", "false");
  }
}
if (surveyModal && submitSurvey) {
  submitSurvey.addEventListener("click", () => {
    profile.grade = document.getElementById("surveyGrade").value;
    profile.subject = document.getElementById("surveySubject").value;
    profile.weakSubject = document.getElementById("surveyWeakSubject").value || "None";
    profile.surveyFilled = true;
    saveJSON("tb_profile", profile);
    surveyModal.classList.add("hidden");
    updateProfileText();
    addMessage("system", `Survey saved! Learning focus set to ${profile.grade} · ${profile.subject}.`);
  });
  
  // Show survey if not filled
  setTimeout(() => {
    maybeShowSurvey();
  }, 1000);
}

// Streak System
function checkStreak() {
  const today = new Date().toDateString();
  const lastActive = profile.lastActiveDate;
  let streak = profile.streak || 0;
  
  if (!lastActive) {
    streak = 1;
  } else {
    const diffTime = Math.abs(new Date(today) - new Date(lastActive));
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays === 1) {
      streak += 1;
    } else if (diffDays > 1) {
      streak = 1;
    }
  }
  profile.streak = streak;
  profile.lastActiveDate = today;
  saveJSON("tb_profile", profile);
  saveProfileToServer();
  
  const streakDisplay = document.getElementById("streakDisplay");
  const streakVal = document.getElementById("streakVal");
  if (streakDisplay && streakVal) {
    streakVal.textContent = streak;
    streakDisplay.style.display = "inline";
  }
}
checkStreak();

// History & Analysis modal
const historyButton = document.getElementById("historyButton");
const historyModal = document.getElementById("historyModal");
const closeHistoryModal = document.getElementById("closeHistoryModal");
const tabStatsBtn = document.getElementById("tabStatsBtn");
const tabHistoryBtn = document.getElementById("tabHistoryBtn");
const historyStatsTab = document.getElementById("historyStatsTab");
const historyLogsTab = document.getElementById("historyLogsTab");
const historyLogsList = document.getElementById("historyLogsList");

if (historyButton && historyModal) {
  historyButton.addEventListener("click", () => {
    // Populate stats
    document.getElementById("analysisSpellScore").textContent = profile.spellScore || 0;
    document.getElementById("analysisStreak").textContent = profile.longestStreak || 0;
    
    let recommendation = "Keep studying to unlock recommendations!";
    if (profile.weakSubject && profile.weakSubject !== "None") {
      recommendation = `We notice you struggle with **${profile.weakSubject}**. Ask TutorBot: "Can you explain ${profile.weakSubject} with a simple example?" or type "/quiz ${profile.weakSubject}".`;
    } else if (profile.subject) {
      recommendation = `Focus on **${profile.subject}**! Click the Quiz button above to take a quick practice assessment.`;
    }
    document.getElementById("analysisRecommendation").innerHTML = renderInline(recommendation);
    
    // Populate chat logs
    historyLogsList.innerHTML = "";
    const logs = loadJSON("tb_chat_logs", []);
    if (!logs.length) {
      historyLogsList.innerHTML = `<li class="log-item" style="color:var(--muted); text-align:center;">No history recorded yet.</li>`;
    } else {
      logs.forEach(log => {
        const li = document.createElement("li");
        li.className = "log-item";
        li.innerHTML = `<div class="log-time">[${log.timestamp}] ${log.role.toUpperCase()}</div><div>${escapeHTML(log.text)}</div>`;
        historyLogsList.appendChild(li);
      });
    }
    
    historyModal.classList.remove("hidden");
    historyModal.setAttribute("aria-hidden", "false");
  });
  
  closeHistoryModal.addEventListener("click", () => {
    historyModal.classList.add("hidden");
    historyModal.setAttribute("aria-hidden", "true");
  });
  
  tabStatsBtn.addEventListener("click", () => {
    tabStatsBtn.classList.add("active");
    tabHistoryBtn.classList.remove("active");
    historyStatsTab.classList.remove("hidden");
    historyLogsTab.classList.add("hidden");
  });
  
  tabHistoryBtn.addEventListener("click", () => {
    tabHistoryBtn.classList.add("active");
    tabStatsBtn.classList.remove("active");
    historyLogsTab.classList.remove("hidden");
    historyStatsTab.classList.add("hidden");
  });
}

function loadSuggestions() {
  // suggestions block is replaced by persistent command buttons.
}

updateProfileText();
checkHealth();
ensureActiveChat();
loadChat(activeChatId);
if (newChatButton) newChatButton.addEventListener("click", maybeStartNewChat);
initCommandButtons();
setInterval(checkHealth, 30000);
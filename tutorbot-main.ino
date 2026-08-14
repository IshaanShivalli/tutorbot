#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <ESPmDNS.h>
#include "DHT.h"
#include <TFT_eSPI.h>

// TFT Display
TFT_eSPI tft = TFT_eSPI();

// LED blink state (declared early -- Arduino auto-generates function
// prototypes right after the #includes, before reaching definitions further
// down, so this enum must exist before any function that uses it in its
// signature or the auto-prototype will fail to compile).
enum LedMode { LED_MODE_RED, LED_MODE_BLUE_BLINK, LED_MODE_GREEN_BLINK };

#include "Face.h"

// LED Pins
#define LED_RED 25
#define LED_BLUE 26
#define LED_GREEN 27

// DHT11 Sensor
#define DHTPIN 14
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// Temperature threshold (Celsius)
#define TEMP_THRESHOLD 40.0
bool serverDisabledDueToHeat = false;

// ---- Coolant mode: triggered by a SUDDEN RISE in the ESP32's own chip
// temperature relative to its NORMAL operating point -- not a fixed offset
// from ambient. An ESP32's die runs naturally 15-30C above ambient just
// from CPU + Wi-Fi/BT self-heating, so a flat "chip - ambient >= 2C" trigger
// (an earlier version of this) would fire constantly and never clear --
// that offset itself IS normal. Instead we track a slow-moving baseline of
// the chip-vs-ambient delta while things are calm, and only trigger when
// the current delta jumps COOLANT_TRIGGER_RISE C or more *above that
// baseline* -- an actual spike, not the everyday offset.
//
// temperatureRead() (built into the ESP32 Arduino core) reads the chip's
// internal sensor; dht.readTemperature() reads ambient air near the board.
// NOTE: temperatureRead() only exists on the original ESP32 (not S2/S3/C3,
// which lack this peripheral), is NOT calibrated per-chip, and reads in
// coarse steps (a few C at a time) rather than smoothly -- treat its
// absolute value as unreliable, only the relative change is meaningful.
// Also: make sure the DHT11 itself isn't mounted right against the board's
// own hot components -- if it's picking up heat radiating off the ESP32/
// regulator rather than genuine surrounding air, "ambient" will be
// inflated too and the whole delta calculation is compromised regardless
// of the logic below.
#define COOLANT_TRIGGER_RISE  2.0   // trigger when delta rises this far above baseline
#define COOLANT_EXIT_RISE     1.0   // exit once it drops back to within this of baseline
#define BASELINE_EMA_ALPHA    0.1   // how fast the baseline adapts to new "normal" (slow, on purpose)
#define BASELINE_WARMUP_READS 3     // don't trigger until the baseline has settled a bit
bool coolantModeActive = false;
float coolantBaselineDelta = NAN;
int coolantBaselineReads = 0;

// Wi-Fi networks in priority order -- serviceWifiConnection() tries #1
// first; if it can't connect within wifiAttemptTimeoutMs, it moves on to
// #2, then #3, #4, then wraps back around to #1 and keeps cycling forever.
// Fill in your real networks here.
struct WifiCredential {
  const char* ssid;
  const char* password;
};

WifiCredential wifiNetworks[] = {
  {"Presidency-WIFI", "P@$RTN1@3#5"},
};

const int wifiNetworkCount = sizeof(wifiNetworks) / sizeof(wifiNetworks[0]);
int currentWifiIndex = 0;

// Server connection status
bool serverConnected = false;
uint32_t lastServerCheck = 0;

// PC server is now reached purely via mDNS -- no broadcast discovery, no
// hardcoded IP. Server.py advertises itself as "tutorbot.local" (see the
// zeroconf registration added there); MDNS.begin() below lets the ESP32's
// underlying mDNS resolver look that hostname up on demand.
const uint16_t pcPort = 5000;
String pcBaseUrl = "http://tutorbot-server.local:5000";
IPAddress resolvedServerIp;
bool serverIpResolved = false;

WebServer server(80);

String pcUrl(const char* path) {
  String base = pcBaseUrl;
  if (base.endsWith("/")) {
    base.remove(base.length() - 1);
  }
  return base + path;
}

// Small helper for call sites that need direct HTTPClient control (e.g.
// handleAiChat(), which reads the response body itself to pull out the
// reply text for chooseExpressionForReply()) instead of going through the
// generic relayJsonPost()/relayGet() wrappers below.
void beginRelay(HTTPClient& http, const char* pcPath, uint32_t timeoutMs) {
  http.setTimeout(timeoutMs);
  http.begin(pcUrl(pcPath));
}

// ---------- LED status (non-blocking blink state machine) ----------
// Previously this just did a single digitalWrite(HIGH) per color, which is
// why "blinking" never actually happened -- there was no blink logic at all.
LedMode currentLedMode = LED_MODE_RED;
bool ledBlinkOn = false;
uint32_t lastLedBlinkToggle = 0;

void setLedMode(LedMode mode) {
  if (mode != currentLedMode) {
    currentLedMode = mode;
    ledBlinkOn = true;          // snap on immediately when mode changes
    lastLedBlinkToggle = millis();
  }
}

// Call every loop() iteration -- handles the actual blinking without delay().
void serviceLedBlink() {
  if (coolantModeActive) {
    // Coolant mode overrides normal status LEDs entirely -- board cools
    // down with everything off except the screen, regardless of Wi-Fi/
    // server state underneath.
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_BLUE, LOW);
    digitalWrite(LED_GREEN, LOW);
    return;
  }

  uint32_t now = millis();
  switch (currentLedMode) {
    case LED_MODE_RED:
      // Solid red: Wi-Fi genuinely not connected, nothing to blink about yet.
      digitalWrite(LED_RED, HIGH);
      digitalWrite(LED_BLUE, LOW);
      digitalWrite(LED_GREEN, LOW);
      break;

    case LED_MODE_BLUE_BLINK: {
      // Fast blink: Wi-Fi is up, server is offline/unreachable -- still
      // retrying continuously in checkServerHealth(), same as Wi-Fi does.
      const uint32_t interval = 300;
      if (now - lastLedBlinkToggle >= interval) {
        lastLedBlinkToggle = now;
        ledBlinkOn = !ledBlinkOn;
      }
      digitalWrite(LED_RED, LOW);
      digitalWrite(LED_BLUE, ledBlinkOn ? HIGH : LOW);
      digitalWrite(LED_GREEN, LOW);
      break;
    }

    case LED_MODE_GREEN_BLINK: {
      // Slow blink: fully online -- a gentle "heartbeat" rather than solid on.
      const uint32_t interval = 10000;
      if (now - lastLedBlinkToggle >= interval) {
        lastLedBlinkToggle = now;
        ledBlinkOn = !ledBlinkOn;
      }
      digitalWrite(LED_RED, LOW);
      digitalWrite(LED_BLUE, LOW);
      digitalWrite(LED_GREEN, ledBlinkOn ? HIGH : LOW);
      break;
    }
  }
}

bool resolveServerHost() {
  if (WiFi.status() != WL_CONNECTED) return false;
  Serial.println("Resolving TutorBot PC server via mDNS...");
  
  // Try querying tutorbot-server first, then tutorbot-pc as fallback
  IPAddress ip = MDNS.queryHost("tutorbot-server", 2000);
  if (ip == INADDR_NONE || ip == IPAddress(0, 0, 0, 0)) {
    ip = MDNS.queryHost("tutorbot-pc", 2000);
  }
  
  if (ip != INADDR_NONE && ip != IPAddress(0, 0, 0, 0)) {
    resolvedServerIp = ip;
    serverIpResolved = true;
    pcBaseUrl = "http://" + ip.toString() + ":5000";
    Serial.print("Discovered TutorBot PC server dynamically at: ");
    Serial.println(pcBaseUrl);
    return true;
  }
  
  return false;
}

bool checkServerHealth() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.setTimeout(3500);
  http.begin(pcBaseUrl + "/health");
  int httpCode = http.GET();
  http.end();

  if (httpCode == 200) {
    return true;
  }

  // If health check failed, re-resolve via mDNS (handles dynamic DHCP IP changes)
  if (resolveServerHost()) {
    HTTPClient retryHttp;
    retryHttp.setTimeout(3500);
    retryHttp.begin(pcBaseUrl + "/health");
    int retryCode = retryHttp.GET();
    retryHttp.end();
    return (retryCode == 200);
  }

  return false;
}

bool wifiEverConnected = false;
uint32_t lastWifiAttempt = 0;
const uint32_t wifiAttemptTimeoutMs = 8000;  // how long to let one network try before moving to the next

// Non-blocking Wi-Fi connect: called every loop() iteration. Never blocks --
// retries continuously in the background, same pattern as checkServerHealth().
// Cycles through wifiNetworks[] -- if the current one hasn't connected within
// wifiAttemptTimeoutMs, moves to the next, wrapping around forever.
void serviceWifiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiEverConnected) {
      wifiEverConnected = true;
      Serial.print("Wi-Fi connected to \"");
      Serial.print(wifiNetworks[currentWifiIndex].ssid);
      Serial.print("\" -- ESP32 relay IP: http://");
      Serial.println(WiFi.localIP());
    }
    return;
  }
  uint32_t now = millis();
  if (now - lastWifiAttempt >= wifiAttemptTimeoutMs) {
    lastWifiAttempt = now;
    currentWifiIndex = (currentWifiIndex + 1) % wifiNetworkCount;
    Serial.print("Wi-Fi not connected -- trying network ");
    Serial.print(currentWifiIndex + 1);
    Serial.print("/");
    Serial.print(wifiNetworkCount);
    Serial.print(": \"");
    Serial.print(wifiNetworks[currentWifiIndex].ssid);
    Serial.println("\"");
    WiFi.disconnect();
    WiFi.begin(wifiNetworks[currentWifiIndex].ssid, wifiNetworks[currentWifiIndex].password);
  }
}

// ---------- Student stats (fetched from Server.py's /student-stats) ----------
int lastLevel = 0, lastXp = 0, lastStreak = 0;
char lastTitle[32] = "";
bool haveStudentStats = false;
uint32_t lastStatsFetch = 0;

// Minimal manual JSON field extraction -- avoids adding ArduinoJson as a new
// dependency for a payload this small/flat. Expects e.g.
// {"level":3,"title":"Rising Star","xp":120,"streak":4}
bool extractIntField(const String& json, const char* key, int& out) {
  String needle = String("\"") + key + "\":";
  int idx = json.indexOf(needle);
  if (idx < 0) return false;
  idx += needle.length();
  out = json.substring(idx).toInt();
  return true;
}

bool extractStringField(const String& json, const char* key, char* out, size_t outLen) {
  String needle = String("\"") + key + "\":\"";
  int idx = json.indexOf(needle);
  if (idx < 0) return false;
  idx += needle.length();
  int end = json.indexOf('"', idx);
  if (end < 0) return false;
  String val = json.substring(idx, end);
  val.toCharArray(out, outLen);
  return true;
}

void fetchStudentStats() {
  if (WiFi.status() != WL_CONNECTED || serverDisabledDueToHeat) return;

  HTTPClient http;
  http.setTimeout(8000);
  http.begin(pcUrl("/student-stats"));
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    int level = 0, xp = 0, streak = 0;
    char title[32] = "";
    bool ok = extractIntField(body, "level", level)
              && extractIntField(body, "xp", xp)
              && extractIntField(body, "streak", streak)
              && extractStringField(body, "title", title, sizeof(title));
    if (ok) {
      lastLevel = level;
      lastXp = xp;
      lastStreak = streak;
      strncpy(lastTitle, title, sizeof(lastTitle) - 1);
      haveStudentStats = true;
    }
  } else {
    Serial.print("fetchStudentStats: request failed, code=");
    Serial.println(code);
  }
  http.end();
}

void enterCoolantMode(float chipTemp, float ambientTemp, float riseFromBaseline) {
  coolantModeActive = true;
  Serial.print("WARNING: ESP32 chip temp jumped ");
  Serial.print(riseFromBaseline, 1);
  Serial.print("C above its normal operating point (baseline delta ");
  Serial.print(coolantBaselineDelta, 1);
  Serial.println("C) -- entering coolant mode (LEDs off, screen sleeping).");
  // serviceLedBlink() picks up coolantModeActive on its own next tick, but
  // switch off immediately here too so there's no one-frame lag/flash.
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_BLUE, LOW);
  digitalWrite(LED_GREEN, LOW);
  enterSleepMode();  // Face.h: draws the sleepy face, stops idle blinking
}

void exitCoolantMode() {
  coolantModeActive = false;
  Serial.println("Chip temp back near its normal baseline -- exiting coolant mode.");
  exitSleepMode();   // Face.h: wakes the face back up to neutral
  updateLedStatus(); // resume normal Wi-Fi/server status LEDs right away
}

void checkTemperature() {
  float humidity = dht.readHumidity();
  float ambientTemp = dht.readTemperature();

  if (isnan(ambientTemp) || isnan(humidity)) {
    Serial.println("DHT11 read failed!");
    return;
  }

  float chipTemp = temperatureRead();  // ESP32 internal sensor (original ESP32 only)
  float delta = chipTemp - ambientTemp;

  // Establish/update the "normal" chip-vs-ambient offset with a slow-moving
  // average -- but never while already in coolant mode, or the baseline
  // would just chase the elevated reading and the trigger could never fire
  // again for a real event.
  if (isnan(coolantBaselineDelta)) {
    coolantBaselineDelta = delta;
    coolantBaselineReads = 1;
  } else if (!coolantModeActive) {
    coolantBaselineDelta += BASELINE_EMA_ALPHA * (delta - coolantBaselineDelta);
    if (coolantBaselineReads < BASELINE_WARMUP_READS) coolantBaselineReads++;
  }

  float riseFromBaseline = delta - coolantBaselineDelta;

  Serial.print("Ambient: ");
  Serial.print(ambientTemp);
  Serial.print("C, ESP32 chip: ");
  Serial.print(chipTemp);
  Serial.print("C (delta ");
  Serial.print(delta, 1);
  Serial.print("C, baseline ");
  Serial.print(coolantBaselineDelta, 1);
  Serial.print("C, rise ");
  Serial.print(riseFromBaseline, 1);
  Serial.print("C), Humidity: ");
  Serial.print(humidity);
  Serial.println("%");

  bool baselineReady = coolantBaselineReads >= BASELINE_WARMUP_READS;
  if (!coolantModeActive && baselineReady && riseFromBaseline >= COOLANT_TRIGGER_RISE) {
    enterCoolantMode(chipTemp, ambientTemp, riseFromBaseline);
  } else if (coolantModeActive && riseFromBaseline <= COOLANT_EXIT_RISE) {
    exitCoolantMode();
  }

  // Separate, pre-existing safety check: room/ambient air itself too hot,
  // regardless of the chip-vs-baseline rise above. Still guards the AI
  // relay specifically.
  if (ambientTemp > TEMP_THRESHOLD && !serverDisabledDueToHeat) {
    Serial.println("WARNING: Ambient temperature too high! Disabling server to cool down...");
    serverDisabledDueToHeat = true;
    serverConnected = false;
  } else if (ambientTemp < (TEMP_THRESHOLD - 5.0) && serverDisabledDueToHeat) {
    Serial.println("Temperature normalized. Server connection re-enabled.");
    serverDisabledDueToHeat = false;
  }
}

void updateLedStatus() {
  if (coolantModeActive) return;  // serviceLedBlink() forces LEDs off during coolant mode

  if (WiFi.status() != WL_CONNECTED) {
    setLedMode(LED_MODE_RED);
    serverConnected = false;
  } else if (serverDisabledDueToHeat) {
    setLedMode(LED_MODE_BLUE_BLINK);
    serverConnected = false;
  } else if (serverConnected) {
    setLedMode(LED_MODE_GREEN_BLINK);
  } else {
    setLedMode(LED_MODE_BLUE_BLINK);
  }
}

// TFT Mouth/Face expression functions (drawMouthHappy, drawMouthThinking,
// drawMouthSad, drawMouthNeutral, drawMouthListening, drawMouthSpeaking,
// blink) now live in Face.h — included near the top of this file.

void sendCorsHeaders() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

void handleOptions() {
  sendCorsHeaders();
  server.send(204);
}

bool wifiUp() {
  return WiFi.status() == WL_CONNECTED;
}

void relayJsonPost(const char* pcPath, uint32_t timeoutMs) {
  if (serverDisabledDueToHeat) {
    server.send(503, "application/json", "{\"error\":\"Server overheating - connection disabled\"}");
    return;
  }
  sendCorsHeaders();

  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"Request body required\"}");
    return;
  }
  if (!wifiUp()) {
    server.send(503, "application/json", "{\"error\":\"ESP32 is not connected to Wi-Fi\"}");
    return;
  }

  HTTPClient http;
  http.setTimeout(timeoutMs);
  http.begin(pcUrl(pcPath));
  http.addHeader("Content-Type", "application/json");

  int statusCode = http.POST(server.arg("plain"));
  String response = statusCode > 0 ? http.getString() : "";
  http.end();

  if (statusCode > 0) {
    server.send(statusCode, "application/json", response);
  } else {
    server.send(502, "application/json", "{\"error\":\"Could not reach TutorBot PC server\"}");
  }
}

void handleRoot() {
  if (LittleFS.exists("/index.html")) {
    File file = LittleFS.open("/index.html", "r");
    if (file) {
      server.streamFile(file, "text/html");
      file.close();
      return;
    }
  }
  String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'>"
                "<title>TutorBot ESP32 Relay</title>"
                "<style>body{font-family:sans-serif;background:#0a0812;color:#f5f2fa;padding:24px;text-align:center;}"
                ".card{max-width:480px;margin:40px auto;background:#1c1830;padding:28px 24px;border-radius:18px;box-shadow:0 4px 20px rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.1);}"
                "h1{color:#a855f7;margin-top:0;}a{color:#38bdf8;text-decoration:none;}code{background:rgba(0,0,0,0.4);padding:3px 7px;border-radius:6px;color:#f5f2fa;font-family:monospace;}"
                ".status{margin:18px 0;padding:12px;border-radius:10px;background:rgba(0,0,0,0.3);font-size:14px;}"
                "</style></head><body><div class='card'>"
                "<h1>TutorBot ESP32 Relay</h1>"
                "<p>ESP32 is online and hosting at: <br><br><code>http://tutorbot.local/</code></p>"
                "<div class='status'>"
                "<p>PC Server Link: <strong style='color:" + String(serverConnected ? "#10b981'>Connected" : "#ef4444'>Searching / Offline") + "</strong></p>"
                "<p style='font-size:12px;color:#a39cb5;margin-top:6px;'>Relay Target: " + pcBaseUrl + "</p>"
                "</div>"
                "<p style='color:#a39cb5;font-size:13px;line-height:1.5;'>To load the full app UI, flash the <code>data/</code> folder using Arduino IDE 'ESP32 LittleFS Data Upload'.</p>"
                "</div></body></html>";
  server.send(200, "text/html", html);
}

void relayGet(const char* pcPath, uint32_t timeoutMs) {
  if (serverDisabledDueToHeat) {
    server.send(503, "application/json", "{\"error\":\"Server overheating - connection disabled\"}");
    return;
  }
  sendCorsHeaders();

  if (!wifiUp()) {
    server.send(503, "application/json", "{\"error\":\"ESP32 is not connected to Wi-Fi\"}");
    return;
  }

  HTTPClient http;
  http.setTimeout(timeoutMs);
  http.begin(pcUrl(pcPath));

  int statusCode = http.GET();
  String response = statusCode > 0 ? http.getString() : "";
  http.end();

  if (statusCode > 0) {
    server.send(statusCode, "application/json", response);
  } else {
    server.send(502, "application/json", "{\"error\":\"Could not reach TutorBot PC server\"}");
  }
}

void handleHealth() {
  sendCorsHeaders();
  server.send(200, "application/json", "{\"ok\":true,\"service\":\"TutorBot ESP32 relay\"}");
}

// Dynamic-length variant of extractStringField (that one takes a fixed char
// buffer, fine for short fields like a title, but the chat reply can be
// hundreds of characters).
bool extractStringFieldDyn(const String& json, const char* key, String& out) {
  String needle = String("\"") + key + "\":\"";
  int idx = json.indexOf(needle);
  if (idx < 0) return false;
  idx += needle.length();
  int end = json.indexOf('"', idx);
  if (end < 0) return false;
  out = json.substring(idx, end);
  return true;
}

// Very light keyword heuristic to pick a mouth expression for the reply --
// not real sentiment analysis, just enough to make the face feel like it's
// actually reacting instead of doing the same animation every single time.
void chooseExpressionForReply(const String& reply) {
  String lower = reply;
  lower.toLowerCase();
  if (lower.indexOf("sorry") >= 0 || lower.indexOf("incorrect") >= 0 ||
      lower.indexOf("error") >= 0 || lower.indexOf("mistake") >= 0 ||
      lower.indexOf("wrong") >= 0) {
    drawMouthSad();
  } else if (lower.indexOf("great") >= 0 || lower.indexOf("correct") >= 0 ||
             lower.indexOf("well done") >= 0 || lower.indexOf("nice") >= 0 ||
             lower.indexOf("awesome") >= 0 || reply.indexOf('!') >= 0) {
    drawMouthHappy();
  } else {
    drawMouthNeutral();
  }
  delay(350); // brief hold so the expression is actually visible before the mouth starts moving
}

void handleAiChat() {
  drawMouthListening();
  drawMouthThinking();

  if (serverDisabledDueToHeat) {
    sendCorsHeaders();
    server.send(503, "application/json", "{\"error\":\"Server overheating - connection disabled\"}");
    drawMouthSad();
    delay(350);
    drawMouthNeutral();
    return;
  }
  sendCorsHeaders();
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"Request body required\"}");
    drawMouthNeutral();
    return;
  }
  if (!wifiUp()) {
    server.send(503, "application/json", "{\"error\":\"ESP32 is not connected to Wi-Fi\"}");
    drawMouthSad();
    delay(350);
    drawMouthNeutral();
    return;
  }

  HTTPClient http;
  beginRelay(http, "/ai-chat", 120000);
  http.addHeader("Content-Type", "application/json");
  int statusCode = http.POST(server.arg("plain"));
  String response = statusCode > 0 ? http.getString() : "";
  http.end();

  if (statusCode > 0) {
    server.send(statusCode, "application/json", response);

    String replyText;
    if (extractStringFieldDyn(response, "response", replyText)) {
      chooseExpressionForReply(replyText);
      // Scale the "speaking" wave duration with reply length -- this is an
      // approximation (the ESP32 doesn't know how long the browser's TTS
      // will actually take to read it aloud), but it's much closer than a
      // fixed ~1s animation regardless of a one-word vs. paragraph reply.
      // Shorter delay between frames than before so the wave reads as
      // continuous motion instead of visible jumps.
      int frames = constrain((int)(replyText.length() / 6), 8, 90);
      for (int i = 0; i < frames; i++) {
        drawMouthSpeaking();
        delay(80);
      }
    } else {
      // Couldn't find a "response" field (e.g. a non-chat payload type) --
      // fall back to the old brief generic flourish.
      for (int i = 0; i < 12; i++) {
        drawMouthSpeaking();
        delay(90);
      }
    }
  } else {
    server.send(502, "application/json", "{\"error\":\"Could not reach TutorBot PC server\"}");
    drawMouthSad();
    delay(350);
  }
  drawMouthNeutral();
}

void handleClear() {
  relayJsonPost("/clear", 15000);
}

void handleCommands() {
  relayGet("/commands", 15000);
}

void handleGenerateSpellWord() {
  relayGet("/generate-spell-word", 15000);
}

void handleStudentStats() {
  relayGet("/student-stats", 15000);
}

void handleDictionary() {
  relayJsonPost("/dictionary", 30000);
}

void handleEsp32SettingsGet() {
  relayGet("/esp32/settings", 15000);
}

void handleEsp32SettingsPost() {
  relayJsonPost("/esp32/settings", 15000);
}

void handleSendOtp() {
  relayJsonPost("/api/send-otp", 20000);
}

void handleVerifyOtp() {
  relayJsonPost("/api/verify-otp", 15000);
}

void handleProcessImage() {
  sendCorsHeaders();
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"No image data provided\"}");
    return;
  }
  if (!wifiUp()) {
    server.send(503, "application/json", "{\"error\":\"ESP32 is not connected to Wi-Fi\"}");
    return;
  }

  HTTPClient http;
  http.setTimeout(60000);
  http.begin(pcUrl("/process-image"));
  if (server.hasHeader("Content-Type")) {
    http.addHeader("Content-Type", server.header("Content-Type"));
  }

  int statusCode = http.POST((uint8_t*)server.arg("plain").c_str(), server.arg("plain").length());
  String response = statusCode > 0 ? http.getString() : "";
  http.end();

  if (statusCode > 0) {
    server.send(statusCode, "application/json", response);
  } else {
    server.send(502, "application/json", "{\"error\":\"Could not reach TutorBot PC server\"}");
  }
}

void handleFilesGet() {
  relayGet("/files", 15000);
}

void handleFilesPost() {
  sendCorsHeaders();
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"No file data provided\"}");
    return;
  }
  if (!wifiUp()) {
    server.send(503, "application/json", "{\"error\":\"ESP32 is not connected to Wi-Fi\"}");
    return;
  }

  HTTPClient http;
  http.setTimeout(60000);
  http.begin(pcUrl("/files"));
  if (server.hasHeader("Content-Type")) {
    http.addHeader("Content-Type", server.header("Content-Type"));
  }

  int statusCode = http.POST((uint8_t*)server.arg("plain").c_str(), server.arg("plain").length());
  String response = statusCode > 0 ? http.getString() : "";
  http.end();

  server.send(statusCode > 0 ? statusCode : 502, "application/json",
              statusCode > 0 ? response : "{\"error\":\"Could not reach TutorBot PC server\"}");
}

void setup() {
  Serial.begin(115200);

  // Initialize TFT display
  tft.init();
  tft.setRotation(0);   // try 0,1,2,3 if orientation looks wrong
  tft.fillScreen(TFT_BLACK);   // clear the default white/garbage init screen immediately
  tft.invertDisplay(false);    // flip to true if colors still look inverted (white bg, wrong colors)

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);

  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_BLUE, LOW);
  digitalWrite(LED_GREEN, LOW);

  dht.begin();
  delay(2000);
  Serial.println("DHT11 sensor initialized");

  drawMouthNeutral();

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP("TutorBot-Relay", "tutorbot123");
  Serial.print("SoftAP active: SSID \"TutorBot-Relay\", IP: http://");
  Serial.println(WiFi.softAPIP());

  currentWifiIndex = 0;
  WiFi.begin(wifiNetworks[currentWifiIndex].ssid, wifiNetworks[currentWifiIndex].password);
  lastWifiAttempt = millis();  // so loop()'s cycling waits its full timeout before trying #2

  Serial.print("Connecting to Wi-Fi (\"");
  Serial.print(wifiNetworks[currentWifiIndex].ssid);
  Serial.print("\")");
  int attempts = 0;
  // Bounded wait here just so mDNS/discovery below have a chance to run
  // immediately if Wi-Fi is quick. If it's not connected within ~8s, we
  // stop blocking and hand off to serviceWifiConnection() in loop(), which
  // cycles through wifiNetworks[] forever in the background instead of
  // getting stuck here.
  while (WiFi.status() != WL_CONNECTED && attempts < 16) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    wifiEverConnected = true;
    Serial.print("ESP32 relay IP: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi not connected yet -- will keep retrying continuously in the background.");
  }

  // mDNS hostnames must be a single label -- no dots.
  // ESP32 hosts the web relay interface at http://tutorbot.local:80
  if (!MDNS.begin("tutorbot")) {
    Serial.println("Error setting up mDNS");
  } else {
    Serial.println("mDNS responder started");
    Serial.println("Access ESP32 at: http://tutorbot.local/");
    MDNS.addService("http", "tcp", 80);
    MDNS.addServiceTxt("http", "tcp", "path", "/");
  }

  // Dynamically resolve the PC server IP on the network
  resolveServerHost();
  Serial.print("Relaying to TutorBot PC server: ");
  Serial.println(pcBaseUrl);

  if (!LittleFS.begin(true)) {
    Serial.println("LittleFS Mount Failed");
    return;
  }
  Serial.println(LittleFS.exists("/index.html"));
  Serial.println(LittleFS.exists("/app.js"));
  Serial.println(LittleFS.exists("/styles.css"));
  Serial.println(LittleFS.exists("/api-config.ts"));
  Serial.println(LittleFS.exists("/api-config.js"));

  server.on("/", HTTP_GET, handleRoot);

  server.serveStatic("/app.js", LittleFS, "/app.js");
  server.serveStatic("/styles.css", LittleFS, "/styles.css");
  server.serveStatic("/api-config.ts", LittleFS, "/api-config.ts");
  server.serveStatic("/api-config.js", LittleFS, "/api-config.js");

  server.on("/health", HTTP_GET, handleHealth);

  server.on("/ai-chat", HTTP_OPTIONS, handleOptions);
  server.on("/ai-chat", HTTP_POST, handleAiChat);

  server.on("/clear", HTTP_OPTIONS, handleOptions);
  server.on("/clear", HTTP_POST, handleClear);

  server.on("/commands", HTTP_GET, handleCommands);
  server.on("/generate-spell-word", HTTP_GET, handleGenerateSpellWord);
  server.on("/generate-spell-word", HTTP_OPTIONS, handleOptions);
  server.on("/api/spell-word", HTTP_GET, handleGenerateSpellWord);
  server.on("/api/spell-word", HTTP_OPTIONS, handleOptions);
  server.on("/student-stats", HTTP_GET, handleStudentStats);

  server.on("/dictionary", HTTP_OPTIONS, handleOptions);
  server.on("/dictionary", HTTP_POST, handleDictionary);

  server.on("/esp32/settings", HTTP_GET, handleEsp32SettingsGet);
  server.on("/esp32/settings", HTTP_OPTIONS, handleOptions);
  server.on("/esp32/settings", HTTP_POST, handleEsp32SettingsPost);

  server.on("/api/send-otp", HTTP_OPTIONS, handleOptions);
  server.on("/api/send-otp", HTTP_POST, handleSendOtp);
  server.on("/api/verify-otp", HTTP_OPTIONS, handleOptions);
  server.on("/api/verify-otp", HTTP_POST, handleVerifyOtp);

  server.on("/process-image", HTTP_OPTIONS, handleOptions);
  server.on("/process-image", HTTP_POST, handleProcessImage);

  server.on("/files", HTTP_GET, handleFilesGet);
  server.on("/files", HTTP_OPTIONS, handleOptions);
  server.on("/files", HTTP_POST, handleFilesPost);

  server.begin();
  Serial.println("TutorBot ESP32 relay started");

  updateLedStatus();
}

void loop() {
  server.handleClient();

  serviceWifiConnection();   // non-blocking, retries forever like the server check below
  serviceLedBlink();         // actually drives the blink now (was missing before)
  faceUpdate();
  if (millis() - lastServerCheck >= 5000) {
    lastServerCheck = millis();
    serverConnected = checkServerHealth();
    updateLedStatus();
    if (!serverConnected && wifiUp()) {
      Serial.print("Server health check failed -- retrying ");
      Serial.print(pcBaseUrl);
      Serial.println("/health in 5s");
    }
  }

  static uint32_t lastTempCheck = 0;
  if (millis() - lastTempCheck >= 10000) {
    lastTempCheck = millis();
    checkTemperature();
    updateLedStatus();
  }

  // Pull the student's stats every 30s and refresh the idle face so the
  // TFT reflects them without interrupting an active chat exchange.
  static uint32_t lastFaceRefresh = 0;
  if (millis() - lastStatsFetch >= 30000) {
    lastStatsFetch = millis();
    fetchStudentStats();
  }
  if (millis() - lastFaceRefresh >= 5000) {
    lastFaceRefresh = millis();
    if (!coolantModeActive) {
      drawMouthNeutral();
    }
  }

  delay(50);
}

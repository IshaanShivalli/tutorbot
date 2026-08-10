#include <WiFi.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <ESPmDNS.h>
#include "DHT.h"
#include <TFT_eSPI.h>
#include "BluetoothA2DPSource.h"

// TFT Display
TFT_eSPI tft = TFT_eSPI();

// LED blink state (declared early -- Arduino auto-generates function
// prototypes right after the #includes, before reaching definitions further
// down, so this enum must exist before any function that uses it in its
// signature or the auto-prototype will fail to compile).
enum LedMode { LED_MODE_RED, LED_MODE_BLUE_BLINK, LED_MODE_GREEN_BLINK };

#include "Face.h"

// ========== Bluetooth speaker (BoAt Stone 170) ==========
// Requires the "ESP32-A2DP" library by pschatzmann (Arduino Library Manager:
// search "ESP32-A2DP"). Classic Bluetooth (A2DP) and Wi-Fi can run together
// on the ESP32, so this doesn't interfere with the relay server above.
//
// NOTE: A2DP streams raw PCM audio that this sketch has to supply via
// btAudioCallback() below. Right now it just sends silence so the speaker
// connects and stays paired -- hook in real audio (e.g. decoded TTS PCM,
// or samples read from a buffer/queue) inside that callback when you have
// an audio source.
BluetoothA2DPSource a2dp_source;
const char* boatSpeakerName = "boAt Stone 170";
bool boatSpeakerConnected = false;

int32_t btAudioCallback(Frame* frame, int32_t frameCount) {
  // Fill with silence by default -- replace this with real PCM samples
  // (e.g. pop them from a ring buffer fed by your audio/TTS pipeline).
  for (int i = 0; i < frameCount; i++) {
    frame[i].channel1 = 0;
    frame[i].channel2 = 0;
  }
  return frameCount;
}

void a2dpConnectionStateCallback(esp_a2d_connection_state_t state, void*) {
  boatSpeakerConnected = (state == ESP_A2D_CONNECTION_STATE_CONNECTED);
  Serial.print("boAt Stone 170 Bluetooth: ");
  Serial.println(boatSpeakerConnected ? "connected" : "not connected");
}

void setupBluetoothSpeaker() {
  a2dp_source.set_auto_reconnect(true);
  a2dp_source.set_on_connection_state_changed(a2dpConnectionStateCallback);
  // start() scans for and connects to a device advertising this name.
  // If your speaker's Bluetooth name differs, update boatSpeakerName above.
  a2dp_source.start(boatSpeakerName, btAudioCallback);
  Serial.print("Searching for Bluetooth speaker: ");
  Serial.println(boatSpeakerName);
}

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
const char* ssid = "daf6net";
const char* password = "NOTYOURNET";

// Server connection status
bool serverConnected = false;
uint32_t lastServerCheck = 0;

String pcBaseUrl = "http://10.173.15.254:5000";
const char* customPcHost = "tutorbot.all.edu.local";
const uint16_t pcPort = 5000;

const unsigned int discoveryPort = 47823;
const char* discoveryMagic = "TUTORBOT_DISCOVER";
WiFiUDP discoveryUdp;

bool pcServerDiscovered = false;
uint32_t lastDiscoveryAttempt = 0;

bool discoverPcServer(uint32_t timeoutMs) {
  discoveryUdp.begin(discoveryPort);
  IPAddress broadcastIp(255, 255, 255, 255);
  discoveryUdp.beginPacket(broadcastIp, discoveryPort);
  discoveryUdp.write((const uint8_t*)discoveryMagic, strlen(discoveryMagic));
  discoveryUdp.endPacket();

  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    int packetSize = discoveryUdp.parsePacket();
    if (packetSize > 0) {
      char buf[128];
      int len = discoveryUdp.read(buf, sizeof(buf) - 1);
      if (len > 0) {
        buf[len] = 0;
        String msg(buf);
        if (msg.startsWith("TUTORBOT_PC:")) {
          String rest = msg.substring(strlen("TUTORBOT_PC:"));
          int sep = rest.lastIndexOf(':');
          if (sep > 0) {
            String ip = rest.substring(0, sep);
            String port = rest.substring(sep + 1);
            pcBaseUrl = "http://" + ip + ":" + port;
            Serial.print("Discovered TutorBot PC server: ");
            Serial.println(pcBaseUrl);
            pcServerDiscovered = true;
            return true;
          }
        }
      }
    }
    delay(50);
  }
  return false;
}

WebServer server(80);

String pcUrl(const char* path) {
  String base = pcBaseUrl;
  if (base.endsWith("/")) {
    base.remove(base.length() - 1);
  }
  return base + path;
}

bool isHttpUrl(const String& value) {
  return value.startsWith("http://") || value.startsWith("https://");
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

bool checkServerHealth() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin(pcBaseUrl + "/health");
  int httpCode = http.GET();
  http.end();

  return (httpCode == 200);
}

bool wifiEverConnected = false;
uint32_t lastWifiAttempt = 0;

// Non-blocking Wi-Fi connect: called every loop() iteration. Never blocks --
// retries continuously in the background, same pattern as checkServerHealth().
void serviceWifiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiEverConnected) {
      wifiEverConnected = true;
      Serial.print("Wi-Fi connected -- ESP32 relay IP: http://");
      Serial.println(WiFi.localIP());
    }
    return;
  }
  uint32_t now = millis();
  if (now - lastWifiAttempt >= 5000) {
    lastWifiAttempt = now;
    Serial.println("Wi-Fi not connected -- retrying...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
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

void checkTemperature() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("DHT11 read failed!");
    return;
  }

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print("°C, Humidity: ");
  Serial.print(humidity);
  Serial.println("%");

  if (temperature > TEMP_THRESHOLD && !serverDisabledDueToHeat) {
    Serial.println("WARNING: Temperature too high! Disabling server to cool down...");
    serverDisabledDueToHeat = true;
    serverConnected = false;
  } else if (temperature < (TEMP_THRESHOLD - 5.0) && serverDisabledDueToHeat) {
    Serial.println("Temperature normalized. Server connection re-enabled.");
    serverDisabledDueToHeat = false;
  }
}

void updateLedStatus() {
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

void applyPcBaseUrl(const String& value) {
  if (value.length() == 0) {
    return;
  }
  if (!isHttpUrl(value)) {
    pcBaseUrl = String("http://") + value + ":" + String(pcPort);
  } else {
    pcBaseUrl = value;
  }
  if (pcBaseUrl.endsWith("/")) {
    pcBaseUrl.remove(pcBaseUrl.length() - 1);
  }
}

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
  File file = LittleFS.open("/index.html", "r");
  if (!file) {
    server.send(500, "text/plain", "index.html not found");
    return;
  }
  server.streamFile(file, "text/html");
  file.close();
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

void handleAiChat() {
  drawMouthListening();
  drawMouthThinking();
  relayJsonPost("/ai-chat", 120000);
  // Animate a brief "speaking" flourish once the reply is ready
  for (int i = 0; i < 6; i++) {
    drawMouthSpeaking();
    delay(180);
  }
  drawMouthNeutral();
}

void handleClear() {
  relayJsonPost("/clear", 15000);
}

void handleCommands() {
  relayGet("/commands", 15000);
}

void handleStudentStats() {
  relayGet("/student-stats", 15000);
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

  // Bluetooth (A2DP) temporarily disabled -- it was crashing
  // ("assert failed: hash_map_set") when the boAt speaker connected,
  // which rebooted the whole board and reset Wi-Fi/LED state.
  // Re-enable once Wi-Fi is confirmed working on its own.
  // setupBluetoothSpeaker();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to Wi-Fi");
  int attempts = 0;
  // Bounded wait here just so mDNS/discovery below have a chance to run
  // immediately if Wi-Fi is quick. If it's not connected within ~8s, we
  // stop blocking and hand off to serviceWifiConnection() in loop(), which
  // retries forever in the background instead of getting stuck here.
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

  if (!MDNS.begin("tutorbot.edu")) {
    Serial.println("Error setting up mDNS");
  } else {
    Serial.println("mDNS responder started");
    Serial.println("Access ESP32 at: http://tutorbot.edu.local/");
    MDNS.addService("http", "tcp", 80);
  }

  applyPcBaseUrl(String(customPcHost));

  Serial.println("Searching for TutorBot PC server on the LAN...");
  if (!discoverPcServer(5000)) {
    Serial.println("Discovery failed -- using the configured custom host or fallback URL.");
  }
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
  server.on("/student-stats", HTTP_GET, handleStudentStats);

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
  static uint8_t consecutiveHealthFailures = 0;
  if (millis() - lastServerCheck >= 5000) {
    lastServerCheck = millis();
    serverConnected = checkServerHealth();
    updateLedStatus();
    if (serverConnected) {
      consecutiveHealthFailures = 0;
    } else if (wifiUp() && consecutiveHealthFailures < 255) {
      consecutiveHealthFailures++;
      // ~30s of failures (6 checks) while on Wi-Fi -- the PC's IP may have
      // changed (new DHCP lease, server moved) even though we discovered it
      // successfully before. Drop the flag so discovery gets retried below.
      if (consecutiveHealthFailures >= 6) {
        pcServerDiscovered = false;
      }
    }
  }

  // If we're on Wi-Fi but haven't got a confirmed-good server URL, retry
  // UDP discovery periodically. Without this, a discovery window missed at
  // boot (e.g. Wi-Fi/Server.py not fully up yet) strands the ESP32 on the
  // unresolvable "tutorbot.all.edu.local" fallback forever, since discovery
  // used to run exactly once in setup(). Short timeout here so it doesn't
  // stall server.handleClient() for long; runs every 15s while unconfirmed.
  if (wifiUp() && !pcServerDiscovered && !serverConnected) {
    if (millis() - lastDiscoveryAttempt >= 15000) {
      lastDiscoveryAttempt = millis();
      Serial.println("Server not reachable -- retrying PC discovery...");
      discoverPcServer(1500);
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
    drawMouthNeutral();
  }

  delay(50);
}

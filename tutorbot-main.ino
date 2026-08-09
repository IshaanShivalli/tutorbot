#include <WiFi.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <ESPmDNS.h>
#include "DHT.h"
#include <TFT_eSPI.h>

// TFT Display
TFT_eSPI tft = TFT_eSPI();

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
const char* ssid = "Airtel-MW40-A5A1";
const char* password = "72442256";

// Server connection status
bool serverConnected = false;
uint32_t lastServerCheck = 0;

String pcBaseUrl = "http://localhost:5000";
const char* customPcHost = "tutorbot.all.edu";
const uint16_t pcPort = 5000;

const unsigned int discoveryPort = 47823;
const char* discoveryMagic = "TUTORBOT_DISCOVER";
WiFiUDP discoveryUdp;

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

void setLedStatus(String status) {
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_BLUE, LOW);
  digitalWrite(LED_GREEN, LOW);

  if (status == "red") {
    digitalWrite(LED_RED, HIGH);
    Serial.println("LED: RED - WiFi not connected");
  } else if (status == "blue") {
    digitalWrite(LED_BLUE, HIGH);
    Serial.println("LED: BLUE - WiFi connected, server offline");
  } else if (status == "green") {
    digitalWrite(LED_GREEN, HIGH);
    Serial.println("LED: GREEN - Fully online");
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
    setLedStatus("red");
    serverConnected = false;
  } else if (serverDisabledDueToHeat) {
    setLedStatus("blue");
    serverConnected = false;
  } else if (serverConnected) {
    setLedStatus("green");
  } else {
    setLedStatus("blue");
  }
}

// ========== TFT Mouth Expression Functions ==========

void drawMouthHappy() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.drawString("TutorBot", 50, 10);

  tft.fillCircle(120, 150, 40, TFT_WHITE);
  tft.fillCircle(105, 140, 5, TFT_BLACK);
  tft.fillCircle(135, 140, 5, TFT_BLACK);

  for (int i = 0; i < 20; i++) {
    int x = 100 + i;
    int y = 160 + (i - 10) * (i - 10) / 20;
    tft.drawPixel(x, y, TFT_BLACK);
  }

  Serial.println("Display: Happy Mouth");
}

void drawMouthThinking() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.drawString("Thinking...", 40, 10);

  tft.fillCircle(120, 150, 40, TFT_WHITE);
  tft.fillCircle(105, 140, 5, TFT_BLACK);
  tft.fillCircle(135, 140, 5, TFT_BLACK);

  tft.drawLine(100, 165, 140, 165, TFT_BLACK);

  tft.fillCircle(120, 95, 3, TFT_YELLOW);

  Serial.println("Display: Thinking Mouth");
}

void drawMouthSad() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.drawString("Error", 60, 10);

  tft.fillCircle(120, 150, 40, TFT_WHITE);
  tft.fillCircle(105, 140, 5, TFT_BLACK);
  tft.fillCircle(135, 140, 5, TFT_BLACK);

  for (int i = 0; i < 20; i++) {
    int x = 100 + i;
    int y = 170 - (i - 10) * (i - 10) / 20;
    tft.drawPixel(x, y, TFT_BLACK);
  }

  Serial.println("Display: Sad Mouth");
}

void drawMouthNeutral() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.drawString("Ready", 50, 10);

  tft.fillCircle(120, 150, 40, TFT_WHITE);
  tft.fillCircle(105, 140, 5, TFT_BLACK);
  tft.fillCircle(135, 140, 5, TFT_BLACK);

  tft.drawLine(100, 165, 140, 165, TFT_BLACK);

  Serial.println("Display: Neutral Mouth");
}

void drawMouthListening() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.drawString("Listening...", 35, 10);

  tft.fillCircle(120, 150, 40, TFT_WHITE);
  tft.fillCircle(105, 140, 5, TFT_BLACK);
  tft.fillCircle(135, 140, 5, TFT_BLACK);

  tft.drawCircle(120, 165, 8, TFT_BLACK);

  Serial.println("Display: Listening Mouth");
}

void drawMouthSpeaking() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.drawString("Speaking...", 40, 10);

  tft.fillCircle(120, 150, 40, TFT_WHITE);
  tft.fillCircle(105, 140, 5, TFT_BLACK);
  tft.fillCircle(135, 140, 5, TFT_BLACK);

  tft.fillRect(105, 160, 30, 12, TFT_BLACK);

  Serial.println("Display: Speaking Mouth");
}

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
  relayJsonPost("/ai-chat", 120000);
}

void handleClear() {
  relayJsonPost("/clear", 15000);
}

void handleCommands() {
  relayGet("/commands", 15000);
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

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to Wi-Fi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println();
  Serial.print("ESP32 relay IP: http://");
  Serial.println(WiFi.localIP());

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

  if (millis() - lastServerCheck >= 5000) {
    lastServerCheck = millis();
    serverConnected = checkServerHealth();
    updateLedStatus();
  }

  static uint32_t lastTempCheck = 0;
  if (millis() - lastTempCheck >= 10000) {
    lastTempCheck = millis();
    checkTemperature();
    updateLedStatus();
  }

  delay(50);
}

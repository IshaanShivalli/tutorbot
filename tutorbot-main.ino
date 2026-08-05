#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

// Replace with your network credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Replace with your PC's local IP and server port
// Example: http://192.168.1.100:5000
const char* pcBaseUrl = "http://192.168.1.100:5000";

WebServer server(80);

String pcUrl(const char* path) {
  return String(pcBaseUrl) + path;
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

void handleHealth() {
  sendCorsHeaders();
  server.send(200, "application/json", "{\"ok\":true,\"service\":\"TutorBot ESP32 relay\"}");
}

void handleAsk() {
  sendCorsHeaders();

  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"Request body required\"}");
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    server.send(503, "application/json", "{\"error\":\"ESP32 is not connected to Wi-Fi\"}");
    return;
  }

  HTTPClient http;
  http.setTimeout(120000);
  http.begin(pcUrl("/ai-chat"));
  http.addHeader("Content-Type", "application/json");

  int statusCode = http.POST(server.arg("plain"));
  String response = http.getString();
  http.end();

  if (statusCode > 0) {
    server.send(statusCode, "application/json", response);
  } else {
    server.send(502, "application/json", "{\"error\":\"Could not reach TutorBot PC server\"}");
  }
}

void handleFileRoutes() {
  sendCorsHeaders();
  if (server.method() == HTTP_POST) {
    // Handle file upload relay
    if (!server.hasArg("plain") && server.args() == 0) {
      server.send(400, "application/json", "{\"error\":\"No file provided\"}");
      return;
    }
    
    if (WiFi.status() != WL_CONNECTED) {
      server.send(503, "application/json", "{\"error\":\"ESP32 not connected to Wi-Fi\"}");
      return;
    }
    
    // Relay file upload to PC server
    HTTPClient http;
    http.setTimeout(180000);
    http.begin(pcUrl("/files"));
    http.addHeader("Content-Type", "multipart/form-data");
    
    int statusCode = http.POST(server.arg("plain"));
    String response = http.getString();
    http.end();
    
    server.send(statusCode, "application/json", response);
  } else {
    // GET request - return info about file operations
    String body = "{";
    body += "\"upload_url\":\"" + pcUrl("/files") + "\",";
    body += "\"list_url\":\"" + pcUrl("/files") + "\",";
    body += "\"note\":\"Files relay through ESP32 to PC. Upload directly to " + pcUrl("/files") + " for best speed.\"";
    body += "}";
    server.send(200, "application/json", body);
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("ESP32 relay: http://");
  Serial.println(WiFi.localIP());
  Serial.print("TutorBot PC server: ");
  Serial.println(pcBaseUrl);

  server.on("/health", HTTP_GET, handleHealth);
  server.on("/ask", HTTP_OPTIONS, handleOptions);
  server.on("/ask", HTTP_POST, handleAsk);
  server.on("/files", HTTP_OPTIONS, handleOptions);
  server.on("/files", HTTP_GET, handleFileRoutes);

  server.begin();
  Serial.println("TutorBot ESP32 relay started");
}

void loop() {
  server.handleClient();
}

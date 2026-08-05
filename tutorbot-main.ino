<<<<<<< HEAD
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

// Fill these in before flashing.
const char* ssid = "Oppo Home 15 2";
const char* password = "basavanilay";

// Use your PC's local IPv4 address, for example:
// http://192.168.1.100:5000
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
  String body = "{";
  body += "\"upload_url\":\"" + pcUrl("/files") + "\",";
  body += "\"list_url\":\"" + pcUrl("/files") + "\",";
  body += "\"note\":\"Upload and download files directly to the PC URL for maximum speed. The ESP32 relays chat.\"";
  body += "}";
  server.send(200, "application/json", body);
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
=======
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

// Replace with your network credentials
const char* ssid = "YOUR_HOME_WIFI_SSID";
const char* password = "YOUR_HOME_WIFI_PASSWORD";

// Replace with your Local PC's IP address and the port your AI backend is running on
const char* pcServerUrl = "http://192.168.1.100:5000/ai-chat"; 

WebServer server(80);

void handleClientRequest() {
  if (server.hasArg("plain") == false) {
    server.send(400, "text/plain", "Body not received");
    return;
  }

  String messageFromPhone = server.arg("plain");
  Serial.println("Received from phone: " + messageFromPhone);

  // Forward the request to the Local PC running the AI model
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(pcServerUrl);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(messageFromPhone);

    if (httpResponseCode > 0) {
      String aiResponse = http.getString();
      Serial.println("Response from PC AI: " + aiResponse);
      
      // Send the AI response back to the mobile phone
      server.send(httpResponseCode, "application/json", aiResponse);
    } else {
      Serial.print("Error sending POST to PC: ");
      Serial.println(httpResponseCode);
      server.send(500, "text/plain", "Failed to reach AI backend on PC");
    }
    http.end();
  } else {
    server.send(503, "text/plain", "ESP32 disconnected from Wi-Fi");
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  
  Serial.println("Connected to WiFi!");
  Serial.print("ESP32 IP Address: http://");
  Serial.println(WiFi.localIP());

  // Define endpoint for mobile phones
  server.on("/ask", HTTP_POST, handleClientRequest);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
>>>>>>> 6696ff70c425dd6f93af6c93d97bcaa324f38300

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
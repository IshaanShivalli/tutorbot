#ifndef FACE_H
#define FACE_H

#include <TFT_eSPI.h>

// Requires a global TFT_eSPI instance named `tft` to already exist
// in the including .ino before this header is used.
extern TFT_eSPI tft;

// ========== Smart-Display Style Face ==========
// Tuned for a 240 (width) x 320 (height) portrait display.
// Style: WiFi icon top-left, blocky twin-bar mouth, minimal.

#define SCREEN_W 240
#define SCREEN_H 320

#define FACE_CX (SCREEN_W / 2)
#define FACE_CY (SCREEN_H / 2)

#define MOUTH_BAR_W   26
#define MOUTH_BAR_GAP 14
#define MOUTH_COLOR   TFT_BLUE
#define EYE_COLOR     TFT_BLUE

// ---------- Status bar (WiFi icon) ----------

inline void drawWifiIcon(int x, int y, bool connected) {
  uint16_t col = connected ? EYE_COLOR : TFT_RED;
  for (int r = 4; r <= 12; r += 4) {
    for (int a = 200; a <= 340; a += 10) {
      float rad = a * 3.14159f / 180.0f;
      int px = x + r * cos(rad);
      int py = y + r * sin(rad);
      tft.drawPixel(px, py, col);
    }
  }
  tft.fillCircle(x, y + 2, 2, col);
}

inline void drawStatusBar(bool wifiConnected) {
  tft.fillRect(0, 0, SCREEN_W, 30, TFT_BLACK);
  drawWifiIcon(20, 18, wifiConnected);
}

// ---------- Base face draw ----------

inline void drawFaceBase(const char* label, bool wifiConnected = true) {
  tft.fillScreen(TFT_BLACK);
  drawStatusBar(wifiConnected);

  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setTextDatum(TC_DATUM);
  tft.drawString(label, SCREEN_W / 2, 8);
  tft.setTextDatum(TL_DATUM);
}

// ---------- Blocky mouth (two rounded bars, like the reference image) ----------

inline void drawMouthBars(int leftH, int rightH) {
  int barY = FACE_CY - 30;
  int leftX  = FACE_CX - MOUTH_BAR_GAP - MOUTH_BAR_W;
  int rightX = FACE_CX + MOUTH_BAR_GAP;

  tft.fillRect(0, barY - 40, SCREEN_W, 100, TFT_BLACK);

  int ly = barY + (60 - leftH) / 2;
  int ry = barY + (60 - rightH) / 2;

  tft.fillRoundRect(leftX,  ly, MOUTH_BAR_W, leftH,  8, MOUTH_COLOR);
  tft.fillRoundRect(rightX, ry, MOUTH_BAR_W, rightH, 8, MOUTH_COLOR);
}

// ---------- Expression states ----------

inline void drawMouthNeutral() {
  drawFaceBase("Ready");
  drawMouthBars(60, 60);
  Serial.println("Display: Neutral");
}

inline void drawMouthHappy() {
  drawFaceBase("TutorBot");
  drawMouthBars(40, 40);
  Serial.println("Display: Happy");
}

inline void drawMouthThinking() {
  drawFaceBase("Thinking...");
  drawMouthBars(20, 20);
  tft.fillCircle(SCREEN_W - 50, 60, 4, TFT_YELLOW);
  tft.fillCircle(SCREEN_W - 35, 45, 6, TFT_YELLOW);
  tft.fillCircle(SCREEN_W - 18, 28, 8, TFT_YELLOW);
  Serial.println("Display: Thinking");
}

inline void drawMouthSad() {
  drawFaceBase("Error");
  drawMouthBars(15, 15);
  tft.fillRect(0, FACE_CY - 30, SCREEN_W, 60, TFT_BLACK);
  tft.drawFastHLine(FACE_CX - 40, FACE_CY, 80, TFT_RED);
  Serial.println("Display: Sad");
}

inline void drawMouthListening() {
  drawFaceBase("Listening...");
  drawMouthBars(50, 50);
  Serial.println("Display: Listening");
}

inline void drawMouthSpeaking() {
  drawFaceBase("Speaking...", true);
  int leftH  = 20 + random(0, 45);
  int rightH = 20 + random(0, 45);
  drawMouthBars(leftH, rightH);
  Serial.println("Display: Speaking (animated)");
}

inline void blink() {
  drawMouthBars(58, 58);
  delay(80);
  drawMouthBars(60, 60);
}

inline void drawClock(const char* hhmm) {
  tft.fillRect(SCREEN_W / 2 - 40, 4, 80, 20, TFT_BLACK);
  tft.setTextColor(TFT_YELLOW);
  tft.setTextSize(2);
  tft.setTextDatum(TC_DATUM);
  tft.drawString(hhmm, SCREEN_W / 2, 8);
  tft.setTextDatum(TL_DATUM);
}

#endif // FACE_H
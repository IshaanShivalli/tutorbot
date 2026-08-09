#ifndef FACE_H
#define FACE_H

#include <TFT_eSPI.h>

// Requires a global TFT_eSPI instance named `tft` to already exist
// in the including .ino before this header is used.
extern TFT_eSPI tft;

// ========== Desktop-Buddy Style Face ==========

#define FACE_CX 120
#define FACE_CY 160
#define EYE_Y   135
#define EYE_DX  35
#define EYE_R   14

inline void drawFaceBase(const char* label) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setTextDatum(TC_DATUM);
  tft.drawString(label, 120, 10);
  tft.setTextDatum(TL_DATUM);
}

inline void drawEyesOpen(int offsetY = 0) {
  tft.fillCircle(FACE_CX - EYE_DX, EYE_Y + offsetY, EYE_R, TFT_CYAN);
  tft.fillCircle(FACE_CX + EYE_DX, EYE_Y + offsetY, EYE_R, TFT_CYAN);
  tft.fillCircle(FACE_CX - EYE_DX, EYE_Y + offsetY, EYE_R * 0.4, TFT_BLACK);
  tft.fillCircle(FACE_CX + EYE_DX, EYE_Y + offsetY, EYE_R * 0.4, TFT_BLACK);
}

inline void drawEyesClosed(int offsetY = 0) {
  tft.drawFastHLine(FACE_CX - EYE_DX - EYE_R, EYE_Y + offsetY, EYE_R * 2, TFT_CYAN);
  tft.drawFastHLine(FACE_CX + EYE_DX - EYE_R, EYE_Y + offsetY, EYE_R * 2, TFT_CYAN);
}

inline void blink() {
  drawEyesClosed();
  delay(120);
  drawEyesOpen();
}

inline void drawMouthHappy() {
  drawFaceBase("TutorBot");
  drawEyesOpen();
  // Wide smiling arc
  for (int x = -35; x <= 35; x++) {
    int y = 200 + (x * x) / 60;
    tft.fillCircle(FACE_CX + x, y, 3, TFT_CYAN);
  }
  Serial.println("Display: Happy Mouth");
}

inline void drawMouthThinking() {
  drawFaceBase("Thinking...");
  drawEyesOpen(-4);
  tft.drawFastHLine(FACE_CX - 20, 205, 40, TFT_CYAN);
  // Thought dots
  tft.fillCircle(190, 60, 4, TFT_YELLOW);
  tft.fillCircle(205, 45, 6, TFT_YELLOW);
  tft.fillCircle(222, 28, 8, TFT_YELLOW);
  Serial.println("Display: Thinking Mouth");
}

inline void drawMouthSad() {
  drawFaceBase("Error");
  drawEyesOpen();
  // Downward frown arc
  for (int x = -30; x <= 30; x++) {
    int y = 215 - (x * x) / 70;
    tft.fillCircle(FACE_CX + x, y, 3, TFT_RED);
  }
  Serial.println("Display: Sad Mouth");
}

inline void drawMouthNeutral() {
  drawFaceBase("Ready");
  drawEyesOpen();
  tft.drawFastHLine(FACE_CX - 25, 202, 50, TFT_CYAN);
  Serial.println("Display: Neutral Mouth");
}

inline void drawMouthListening() {
  drawFaceBase("Listening...");
  drawEyesOpen();
  tft.fillCircle(FACE_CX, 205, 10, TFT_CYAN);
  tft.fillCircle(FACE_CX, 205, 5, TFT_BLACK);
  Serial.println("Display: Listening Mouth");
}

inline void drawMouthSpeaking() {
  drawFaceBase("Speaking...");
  drawEyesOpen();
  static bool open = false;
  open = !open;
  int h = open ? 20 : 8;
  tft.fillRoundRect(FACE_CX - 22, 200 - h / 2, 44, h, 6, TFT_CYAN);
  Serial.println("Display: Speaking Mouth");
}

#endif // FACE_H
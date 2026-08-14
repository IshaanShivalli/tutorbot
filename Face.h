#ifndef FACE_H
#define FACE_H

#include <TFT_eSPI.h>
#include <math.h>

extern TFT_eSPI tft;
#define SCREEN_W 240
#define SCREEN_H 320

#define FACE_CX (SCREEN_W / 2)
#define FACE_CY (SCREEN_H / 2)

#define FACE_COLOR   TFT_RED
#define EYE_COLOR    TFT_RED
#define HILITE_COLOR TFT_WHITE
#define BG_COLOR     TFT_BLACK

#define EYE_W      36
#define EYE_H      42
#define EYE_RADIUS 10
#define EYE_GAP    26
#define EYE_Y      (FACE_CY - 60)

inline void drawEyes(int squishPct = 0) {
  int h = EYE_H - (EYE_H * squishPct) / 100;
  if (h < 2) h = 2;
  int leftX  = FACE_CX - EYE_GAP / 2 - EYE_W;
  int rightX = FACE_CX + EYE_GAP / 2;
  int y = EYE_Y + (EYE_H - h) / 2;

  tft.fillRect(leftX - 6, EYE_Y - 6, EYE_W + 12, EYE_H + 12, BG_COLOR);
  tft.fillRect(rightX - 6, EYE_Y - 6, EYE_W + 12, EYE_H + 12, BG_COLOR);

  tft.fillRoundRect(leftX,  y, EYE_W, h, EYE_RADIUS, EYE_COLOR);
  tft.fillRoundRect(rightX, y, EYE_W, h, EYE_RADIUS, EYE_COLOR);

  if (squishPct < 60) {
    int hiR = 4;
    int hiY = y + hiR + 3;
    tft.fillCircle(leftX + EYE_W - 10, hiY, hiR, HILITE_COLOR);
    tft.fillCircle(rightX + EYE_W - 10, hiY, hiR, HILITE_COLOR);
  }
}

#define MOUTH_Y        (FACE_CY + 55)
#define MOUTH_ZONE_H   50
#define MOUTH_SEGS     7
#define MOUTH_SEG_W    7
#define MOUTH_SEG_GAP  3
#define MOUTH_SEG_H    8

inline void clearMouthZone() {
  tft.fillRect(0, MOUTH_Y - MOUTH_ZONE_H / 2, SCREEN_W, MOUTH_ZONE_H, BG_COLOR);
}

inline void drawMouthCurve(int curvature, int width = -1) {
  clearMouthZone();
  int segW = MOUTH_SEG_W;
  int step = segW + MOUTH_SEG_GAP;
  int totalW = (width > 0) ? width : MOUTH_SEGS * step - MOUTH_SEG_GAP;
  int segs = totalW / step;
  if (segs < 3) segs = 3;
  int startX = FACE_CX - (segs * step - MOUTH_SEG_GAP) / 2;
  int mid = (segs - 1) / 2.0f;

  for (int i = 0; i < segs; i++) {
    float d = i - (segs - 1) / 2.0f;          
    float maxD = (segs - 1) / 2.0f;
    float shape = (maxD > 0) ? (1.0f - (d * d) / (maxD * maxD)) : 1.0f;
    int yOffset = (int)(curvature * shape);
    int x = startX + i * step;
    int y = MOUTH_Y + yOffset - MOUTH_SEG_H / 2;
    tft.fillRoundRect(x, y, segW, MOUTH_SEG_H, MOUTH_SEG_H / 2, FACE_COLOR);
  }
}


inline void drawMouthOpen(int w, int h) {
  clearMouthZone();
  int x = FACE_CX - w / 2;
  int y = MOUTH_Y - h / 2;
  tft.fillRoundRect(x, y, w, h, min(w, h) / 2, FACE_COLOR);
}


inline void drawFaceBase() {
  tft.fillScreen(BG_COLOR);
  drawEyes(0);
}


inline void drawMouthNeutral() {
  drawFaceBase();
  drawMouthCurve(0);
  Serial.println("Display: Neutral");
}

inline void drawMouthHappy() {
  drawFaceBase();
  drawMouthCurve(10);          
  Serial.println("Display: Happy");
}

inline void drawMouthSad() {
  drawFaceBase();
  drawMouthCurve(-10);         
  Serial.println("Display: Sad");
}

inline void drawMouthListening() {
  drawFaceBase();
  drawMouthOpen(18, 18);
  Serial.println("Display: Listening");
}


inline void drawMouthThinking() {
  drawFaceBase();
  drawMouthCurve(0, 30);
  Serial.println("Display: Thinking");
}

inline void animateThinkingDots(uint32_t nowMs) {
  int phase = (nowMs / 250) % 3;
  int dotY = MOUTH_Y + MOUTH_ZONE_H / 2 + 14;
  tft.fillRect(0, dotY - 5, SCREEN_W, 12, BG_COLOR);
  for (int i = 0; i < 3; i++) {
    int r = (i == phase) ? 4 : 2;
    int x = FACE_CX - 16 + i * 16;
    tft.fillCircle(x, dotY, r, FACE_COLOR);
  }
}

#define WAVE_BARS    9
#define WAVE_BAR_W   6
#define WAVE_BAR_GAP 4
#define WAVE_MAX_H   30
#define WAVE_MIN_H   6

inline void drawMouthWave(float phase) {
  clearMouthZone();
  int step = WAVE_BAR_W + WAVE_BAR_GAP;
  int totalW = WAVE_BARS * step - WAVE_BAR_GAP;
  int startX = FACE_CX - totalW / 2;
  float maxD = (WAVE_BARS - 1) / 2.0f;

  for (int i = 0; i < WAVE_BARS; i++) {
    float d = i - maxD;
    float envelope = 1.0f - fabsf(d) / (maxD + 1.0f);   
    float s = sinf(phase + d * 0.8f);                   
    int h = WAVE_MIN_H + (int)((WAVE_MAX_H - WAVE_MIN_H) * envelope * (0.5f + 0.5f * s));
    if (h < WAVE_MIN_H) h = WAVE_MIN_H;
    int x = startX + i * step;
    int y = MOUTH_Y - h / 2;
    tft.fillRoundRect(x, y, WAVE_BAR_W, h, WAVE_BAR_W / 2, FACE_COLOR);
  }
}

inline void drawMouthSpeaking() {
  drawMouthWave(millis() * 0.006f);
}

inline void drawClosedEyes() {
  int leftX  = FACE_CX - EYE_GAP / 2 - EYE_W;
  int rightX = FACE_CX + EYE_GAP / 2;
  int y = EYE_Y + EYE_H / 2 - 2;

  tft.fillRect(leftX - 6, EYE_Y - 6, EYE_W + 12, EYE_H + 12, BG_COLOR);
  tft.fillRect(rightX - 6, EYE_Y - 6, EYE_W + 12, EYE_H + 12, BG_COLOR);

  tft.fillRoundRect(leftX,  y, EYE_W, 4, 2, EYE_COLOR);
  tft.fillRoundRect(rightX, y, EYE_W, 4, 2, EYE_COLOR);
}

inline void drawFaceSleepy() {
  tft.fillScreen(BG_COLOR);
  drawClosedEyes();
  drawMouthCurve(0, 20);   
  Serial.println("Display: Sleepy (coolant mode)");
}

inline void animateSleepyZzz(uint32_t nowMs) {
  int cycle = (nowMs / 700) % 4;   
  int x = SCREEN_W - 66;
  int y = EYE_Y - 46;

  tft.fillRect(x - 8, y - 8, 74, 46, BG_COLOR);
  tft.setTextColor(FACE_COLOR);
  tft.setTextDatum(TL_DATUM);

  const int sizes[3] = {1, 2, 3};
  const int xs[3]     = {x, x + 16, x + 34};
  const int ys[3]     = {y + 26, y + 12, y};

  for (int i = 0; i < 3; i++) {
    if (i <= cycle) {
      tft.setTextSize(sizes[i]);
      tft.drawString("Z", xs[i], ys[i]);
    }
  }
}

static bool g_faceSleeping = false;

inline void enterSleepMode() {
  g_faceSleeping = true;
  drawFaceSleepy();
}

inline void exitSleepMode() {
  g_faceSleeping = false;
  drawMouthNeutral();
}

inline void faceUpdate() {
  if (g_faceSleeping) {
    static uint32_t lastZzzFrame = 0;
    uint32_t now = millis();
    if (now - lastZzzFrame >= 300) {
      lastZzzFrame = now;
      animateSleepyZzz(now);
    }
    return;  
  }

  static uint32_t nextBlinkAt = 0;
  static uint32_t blinkStartedAt = 0;
  static bool blinking = false;
  static uint32_t nowSeedInit = 0;

  uint32_t now = millis();

  if (nextBlinkAt == 0) {
    nextBlinkAt = now + 2000 + random(0, 3000);
  }

  if (!blinking && now >= nextBlinkAt) {
    blinking = true;
    blinkStartedAt = now;
  }

  if (blinking) {
    uint32_t elapsed = now - blinkStartedAt;
    const uint32_t blinkDurationMs = 220;
    if (elapsed >= blinkDurationMs) {
      blinking = false;
      drawEyes(0);
      nextBlinkAt = now + 2500 + random(0, 4000); 
    } else {
      float t = (float)elapsed / blinkDurationMs;
      int squish = (t < 0.5f) ? (int)(t * 2 * 100) : (int)((1.0f - t) * 2 * 100);
      drawEyes(squish);
    }
  }
}

inline void blink() {
  drawEyes(90);
  delay(80);
  drawEyes(0);
}

inline void drawStudentStats(int level, int xp, int streak, const char* title) {
  int y = SCREEN_H - 60;
  tft.fillRect(0, y - 6, SCREEN_W, 66, BG_COLOR);

  char line1[48];
  char line2[48];
  snprintf(line1, sizeof(line1), "Lv %d - %s", level, title);
  snprintf(line2, sizeof(line2), "XP %d   Streak %d", xp, streak);

  tft.setTextColor(TFT_GREEN);
  tft.setTextSize(1);
  tft.setTextDatum(TL_DATUM);
  tft.drawString(line1, 10, y);
  tft.drawString(line2, 10, y + 16);
}

#endif
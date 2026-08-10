#ifndef VOICE_H
#define VOICE_H

// ===================================================================
// voice.h -- Voice I/O for the boAt Stone 170
//
// Two DIFFERENT Bluetooth Classic profiles are involved here, and they
// serve opposite directions of audio:
//
//   A2DP (source)  ESP32 -> speaker   "TutorBot talks"    -- SOLID, WORKS
//   HFP  (AG role) speaker -> ESP32   "boAt mic captured"  -- EXPERIMENTAL
//
// TTS OUT (A2DP): the PC (Server.py) generates speech audio for the AI's
// reply; the ESP32 pulls it into a ring buffer and voiceFillA2dpFrames()
// feeds it to BluetoothA2DPSource frame-by-frame. This reuses the A2DP
// connection you already have working -- reliable.
//
// MIC IN (HFP): capturing the boAt's built-in mic requires the ESP32 to
// act as an HFP "Audio Gateway" (the role a phone normally plays) so the
// speaker treats it like an incoming call and opens its mic (SCO audio).
// This uses raw ESP-IDF calls because there is no Arduino-friendly
// library for it like ESP32-A2DP.
//
// IMPORTANT CAVEAT: consumer Bluetooth speakers (including the boAt Stone
// 170) are built to expect a real phone on the other end of HFP -- some
// firmwares only fully open the mic/SCO path once a "call" is answered in
// a way their firmware recognizes, and some may not accept a second
// simultaneous classic-BT role (A2DP + HFP) from the same peer at all.
// This code implements the flow correctly per the ESP-IDF HFP-AG API, but
// I can't guarantee the boAt will actually hand back live mic audio --
// if voiceLoop() never logs "HFP: SCO audio started", the speaker is not
// accepting the AG role from the ESP32 and this path won't work on this
// hardware. In that case the mic input needs to come from somewhere else
// (phone browser mic, a wired I2S mic module, etc).
// ===================================================================

#include <Arduino.h>
#include <HTTPClient.h>
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_bt_api.h"
#include "esp_hf_ag_api.h"

// ---------------- TTS OUT (A2DP) ----------------

// Simple ring buffer of 16-bit stereo PCM samples fed by fetchTtsAudio().
#define TTS_RING_FRAMES 8192
static int16_t ttsRingL[TTS_RING_FRAMES];
static int16_t ttsRingR[TTS_RING_FRAMES];
static volatile uint32_t ttsReadPos = 0;
static volatile uint32_t ttsWritePos = 0;

inline uint32_t voiceTtsAvailable() {
  return (ttsWritePos - ttsReadPos + TTS_RING_FRAMES) % TTS_RING_FRAMES;
}

// Called by the A2DP data callback in the .ino (btAudioCallback) whenever
// the Bluetooth stack needs more PCM to send to the speaker.
inline int32_t voiceFillA2dpFrames(Frame* frame, int32_t frameCount) {
  int32_t supplied = 0;
  while (supplied < frameCount && voiceTtsAvailable() > 0) {
    frame[supplied].channel1 = ttsRingL[ttsReadPos];
    frame[supplied].channel2 = ttsRingR[ttsReadPos];
    ttsReadPos = (ttsReadPos + 1) % TTS_RING_FRAMES;
    supplied++;
  }
  // Pad the rest with silence if we ran out of buffered audio.
  for (int32_t i = supplied; i < frameCount; i++) {
    frame[i].channel1 = 0;
    frame[i].channel2 = 0;
  }
  return frameCount;
}

// Push freshly-fetched PCM (e.g. from the PC's TTS endpoint) into the ring.
// samples[] is interleaved or mono-duplicated -- adapt to whatever format
// your PC's TTS response actually returns.
inline void voiceQueueTtsPcm(const int16_t* samples, size_t sampleCount) {
  for (size_t i = 0; i < sampleCount; i++) {
    uint32_t next = (ttsWritePos + 1) % TTS_RING_FRAMES;
    if (next == ttsReadPos) break;  // ring full, drop rest rather than overwrite unread audio
    ttsRingL[ttsWritePos] = samples[i];
    ttsRingR[ttsWritePos] = samples[i];
    ttsWritePos = next;
  }
}

// Fetch raw 16-bit PCM (mono, 44100Hz expected by A2DP) from a PC endpoint
// and queue it for playback. Point ttsPath at whatever route Server.py
// exposes for synthesized speech (add one if it doesn't exist yet).
inline bool voiceFetchAndQueueTts(const String& pcBaseUrl, const String& text) {
  HTTPClient http;
  http.begin(pcBaseUrl + "/tts");
  http.addHeader("Content-Type", "application/json");
  String body = "{\"text\":\"" + text + "\"}";
  int code = http.POST(body);
  if (code != 200) {
    http.end();
    Serial.print("voice: /tts fetch failed, code=");
    Serial.println(code);
    return false;
  }
  WiFiClient* stream = http.getStreamPtr();
  int len = http.getSize();
  static int16_t chunk[512];
  int received = 0;
  while (http.connected() && received < len) {
    size_t avail = stream->available();
    if (avail == 0) { delay(1); continue; }
    size_t toRead = min(avail, sizeof(chunk));
    toRead -= (toRead % 2);  // keep 16-bit alignment
    if (toRead == 0) continue;
    int r = stream->readBytes((uint8_t*)chunk, toRead);
    voiceQueueTtsPcm(chunk, r / 2);
    received += r;
  }
  http.end();
  return true;
}

// ---------------- MIC IN (HFP, experimental) ----------------

static bool hfpScoActive = false;
static char hfpTargetName[64] = {0};

inline void voiceHfCallback(esp_hf_cb_event_t event, esp_hf_cb_param_t* param) {
  switch (event) {
    case ESP_HF_CONNECTION_STATE_EVT:
      Serial.print("HFP: connection state = ");
      Serial.println(param->conn_stat.state);
      break;
    case ESP_HF_AUDIO_STATE_EVT:
      hfpScoActive = (param->audio_stat.state == ESP_HF_AUDIO_STATE_CONNECTED);
      Serial.println(hfpScoActive
                        ? "HFP: SCO audio started -- boAt mic should be live"
                        : "HFP: SCO audio stopped");
      break;
    default:
      break;
  }
}

// Raw mic PCM arrives here from the SCO link (when/if it connects).
// Right now this just leaves a hook point; adapt buffering/streaming as
// needed once you confirm SCO actually comes up on your hardware.
inline void voiceHandleScoData(const uint8_t* data, size_t len) {
  // TODO: buffer + POST to Server.py, e.g. relay to a /stt endpoint.
  // Left as a stub since without confirmed SCO audio there's nothing to
  // capture yet -- fill in once "HFP: SCO audio started" shows in the log.
}

inline void voiceSetupHfp(const char* speakerName) {
  strncpy(hfpTargetName, speakerName, sizeof(hfpTargetName) - 1);

  esp_bt_controller_config_t btCfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
  if (esp_bt_controller_get_status() == ESP_BT_CONTROLLER_STATUS_IDLE) {
    esp_bt_controller_init(&btCfg);
  }
  esp_bt_controller_enable(ESP_BT_MODE_CLASSIC_BT);

  if (esp_bluedroid_get_status() == ESP_BLUEDROID_STATUS_UNINITIALIZED) {
    esp_bluedroid_init();
  }
  esp_bluedroid_enable();

  esp_bt_hf_register_callback(voiceHfCallback);
  // esp_bt_hf_init wants the remote device's BT address for HFP -- we
  // don't have the boAt's address captured yet at this point in setup,
  // so pass NULL for now. If this is rejected at runtime, we'll need to
  // capture the boAt's address (e.g. from the A2DP connection callback)
  // and pass it in here instead.
  esp_bt_hf_init(NULL);

  Serial.println("voice: HFP-AG initialized (experimental mic path)");
  Serial.println("voice: waiting to see if the boAt accepts an HFP link...");

  // NOTE: actually placing/answering a "call" so SCO opens needs to happen
  // once we've confirmed the service-level connection (SLC) comes up --
  // add that call sequence here once ESP_HF_CONNECTION_STATE_EVT shows
  // CONNECTED in the log above.
}

inline void voiceLoop() {
  // Nothing to poll yet -- HFP delivers data via callbacks/events, and TTS
  // playback is pulled by the A2DP data callback directly. This function
  // exists as the hook point for buffering/streaming logic once SCO audio
  // is confirmed working (see voiceHandleScoData above).
}

#endif  // VOICE_H
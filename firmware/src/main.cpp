// ── InkSight Firmware ────────────────────────────────────────
// Smart e-ink desktop companion powered by LLM
// https://github.com/datascale-ai/inksight

#include <Arduino.h>
#include <WiFi.h>

#include "config.h"
#include "epd_driver.h"
#include "display.h"
#include "network.h"
#include "storage.h"
#include "portal.h"

// ── Shared framebuffer (referenced by other modules via extern) ──
uint8_t imgBuf[IMG_BUF_LEN];

// ── Runtime state ───────────────────────────────────────────
static unsigned long cfgBtnPressStart = 0;
static unsigned long lastSecTick;
static unsigned long setupDoneMillis;

// ── Forward declarations ────────────────────────────────────
static void checkConfigButton();
static void handleFailure(const char *reason);

// ═════════════════════════════════════════════════════════════
// setup()
// ═════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);
    delay(3000);
    Serial.println("\n=== InkSight ===");

    gpioInit();
    epdInit();
    Serial.println("EPD ready");

    loadConfig();

    // Check if config button is held or no WiFi config exists
    bool forcePortal = (digitalRead(PIN_CFG_BTN) == LOW);
    bool hasConfig   = (cfgSSID.length() > 0);

    if (forcePortal || !hasConfig) {
        Serial.println(forcePortal ? "Config button held -> portal"
                                   : "No WiFi config -> portal");

        String mac = WiFi.macAddress();
        String apName = "InkSight-" + mac.substring(mac.length() - 5);
        apName.replace(":", "");

        showSetupScreen(apName.c_str());
        startCaptivePortal();
        return;
    }

    // Normal boot: connect WiFi and fetch image
    int retryCount = getRetryCount();
    Serial.printf("Retry count: %d/%d\n", retryCount, MAX_RETRY_COUNT);

    if (!connectWiFi()) {
        handleFailure("WiFi failed");
        return;
    }

    Serial.println("Fetching image...");
    if (!fetchBMP()) {
        handleFailure("Server error");
        return;
    }

    // Success - reset retry counter
    resetRetryCount();

    Serial.println("Displaying image...");
    epdDisplay(imgBuf);
    Serial.println("Display done");

    syncNTP();

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);

    lastSecTick = millis();
    setupDoneMillis = millis();

    Serial.printf("Time tracking started: %02d:%02d:%02d\n", curHour, curMin, curSec);
#if DEBUG_MODE
    Serial.printf("[DEBUG] Content refresh every %d min (user config: %d min)\n",
                  DEBUG_REFRESH_MIN, cfgSleepMin);
#else
    Serial.printf("Content refresh every %d min\n", cfgSleepMin);
#endif
}

// ═════════════════════════════════════════════════════════════
// loop()
// ═════════════════════════════════════════════════════════════

void loop() {
    // Portal mode: only handle web requests
    if (portalActive) {
        handlePortalClients();
        delay(5);
        return;
    }

    unsigned long now = millis();

    checkConfigButton();

    // Periodic content refresh
#if DEBUG_MODE
    unsigned long refreshInterval = DEBUG_REFRESH_MIN * 60000UL;
#else
    unsigned long refreshInterval = (unsigned long)cfgSleepMin * 60000UL;
#endif

    if (now - setupDoneMillis >= refreshInterval) {
#if DEBUG_MODE
        Serial.printf("%d min elapsed, refreshing content...\n", DEBUG_REFRESH_MIN);
#else
        Serial.printf("%d min elapsed, refreshing content...\n", cfgSleepMin);
#endif
        if (connectWiFi()) {
            if (fetchBMP()) {
                Serial.println("Displaying new content...");
                epdDisplay(imgBuf);
                Serial.println("Display done");
                syncNTP();
            } else {
                Serial.println("Fetch failed, keeping old content");
            }
            WiFi.disconnect(true);
            WiFi.mode(WIFI_OFF);
        } else {
            Serial.println("WiFi reconnect failed, keeping old content");
        }

        setupDoneMillis = millis();
        lastSecTick = millis();
    }

    // Update time display every second (partial refresh)
    if (now - lastSecTick >= 1000) {
        lastSecTick = now;
        tickTime();
        updateTimeDisplay();
    }

    delay(50);
}

// ── Failure handler with retry logic ────────────────────────

static void handleFailure(const char *reason) {
    showError(reason);
    epdSleep();

    int retryCount = getRetryCount();
    if (retryCount < MAX_RETRY_COUNT) {
        setRetryCount(retryCount + 1);
        Serial.printf("%s, retry %d/%d in %ds...\n",
                      reason, retryCount + 1, MAX_RETRY_COUNT, RETRY_DELAY_SEC);
        delay(RETRY_DELAY_SEC * 1000);
        ESP.restart();
    } else {
        Serial.println("Max retries reached, entering deep sleep");
        resetRetryCount();
        esp_sleep_enable_timer_wakeup((uint64_t)cfgSleepMin * 60ULL * 1000000ULL);
        esp_deep_sleep_start();
    }
}

// ── Config button handler (long press to enter portal) ──────

static void checkConfigButton() {
    bool isPressed = (digitalRead(PIN_CFG_BTN) == LOW);

    if (isPressed) {
        if (cfgBtnPressStart == 0) {
            cfgBtnPressStart = millis();
            Serial.println("Config button pressed");
        } else {
            unsigned long holdTime = millis() - cfgBtnPressStart;
            if (holdTime >= (unsigned long)CFG_BTN_HOLD_MS) {
                Serial.printf("Config button held for %dms, restarting...\n", CFG_BTN_HOLD_MS);
                showError("Restarting");
                delay(1000);
                ESP.restart();
            }
        }
    } else {
        if (cfgBtnPressStart != 0) {
            Serial.printf("Config button released after %lums\n", millis() - cfgBtnPressStart);
        }
        cfgBtnPressStart = 0;
    }
}

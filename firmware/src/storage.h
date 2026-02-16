#ifndef INKSIGHT_STORAGE_H
#define INKSIGHT_STORAGE_H

#include <Arduino.h>

// ── Runtime config variables (populated from NVS) ───────────
extern String cfgSSID;
extern String cfgPass;
extern String cfgServer;
extern int    cfgSleepMin;
extern String cfgConfigJson;

// ── NVS operations ──────────────────────────────────────────

// Load all config from NVS into runtime variables
void loadConfig();

// Save WiFi credentials to NVS
void saveWiFiConfig(const String &ssid, const String &pass);

// Save user config JSON to NVS (also extracts refreshInterval)
void saveUserConfig(const String &configJson);

// Retry counter management
int  getRetryCount();
void setRetryCount(int count);
void resetRetryCount();

#endif // INKSIGHT_STORAGE_H

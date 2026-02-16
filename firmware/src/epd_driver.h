#ifndef INKSIGHT_EPD_DRIVER_H
#define INKSIGHT_EPD_DRIVER_H

#include <Arduino.h>

// Initialize GPIO pins for EPD and config button
void gpioInit();

// Initialize EPD controller (Waveshare 4.2" V2, SSD1683)
void epdInit();

// Full-screen display refresh
void epdDisplay(const uint8_t *image);

// Partial display refresh for a rectangular region
void epdPartialDisplay(uint8_t *data, int xStart, int yStart, int xEnd, int yEnd);

// Put EPD into deep sleep mode
void epdSleep();

#endif // INKSIGHT_EPD_DRIVER_H

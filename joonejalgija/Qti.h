#pragma once
#include <Arduino.h>
#include "Config.h"
#include "Globals.h"

/**
 * @file Qti.h
 * @brief Inline helpers for battery and QTI sensor reading.
 */

/**
 * @brief Reads battery voltage and returns moving-average value in millivolts.
 *
 * Reads the analog battery sense pin, converts the ADC value to millivolts
 * using the configured ADC reference, compensates for the voltage divider,
 * stores the newest value into a circular buffer, and returns the average
 * of buffered samples.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Averaged battery voltage in millivolts
 */
inline uint16_t readBatteryMv() {
  const uint32_t adc = analogRead(PIN_BATTERY);

  const uint32_t instant_mv =
      (adc * ADC_REFERENCE_MV * BATTERY_DIVIDER_RATIO) / ADC_MAX_VALUE;

  g_battery_buffer[g_battery_buffer_index] = (uint16_t)instant_mv;
  g_battery_buffer_index++;

  if (g_battery_buffer_index >= BATTERY_FILTER_SAMPLES) {
    g_battery_buffer_index = 0;
  }

  if (g_battery_buffer_count < BATTERY_FILTER_SAMPLES) {
    g_battery_buffer_count++;
  }

  uint32_t sum_mv = 0;
  for (uint8_t i = 0; i < g_battery_buffer_count; i++) {
    sum_mv += g_battery_buffer[i];
  }

  if (g_battery_buffer_count == 0) {
    return (uint16_t)instant_mv;
  }

  return (uint16_t)(sum_mv / g_battery_buffer_count);
}

/**
 * @brief Measures QTI sensor discharge time on the selected pin.
 *
 * Charges the sensor input, switches the pin to input mode, and measures
 * how long the signal stays high.
 *
 * @param[in]  pin QTI sensor pin
 * @param[out] none
 * @return     Measured discharge time in microseconds
 */
inline unsigned int readQtiTime(uint8_t pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, HIGH);
  delayMicroseconds(QTI_CHARGE_DELAY_US);

  pinMode(pin, INPUT);
  const unsigned long start_us = micros();

  while (digitalRead(pin) == HIGH) {
    if ((micros() - start_us) > QTI_TIMEOUT_US) {
      break;
    }
  }

  return (unsigned int)(micros() - start_us);
}
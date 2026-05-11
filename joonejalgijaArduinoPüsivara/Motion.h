#pragma once
#include <Arduino.h>
#include "Globals.h"

/**
 * @file Motion.h
 * @brief Inline helpers for wheel and LED control.
 */

/**
 * @brief Clamps a motor pulse width to the allowed delta range.
 *
 * @param[in]  value_us Requested pulse width in microseconds
 * @param[out] none
 * @return     Safe pulse width in microseconds
 */
inline int clampMotorPulse(int value_us) {
  const int left_min  = SERVO_STOP_LEFT_US  - (int)g_motor_delta_limit;
  const int left_max  = SERVO_STOP_LEFT_US  + (int)g_motor_delta_limit;
  const int right_min = SERVO_STOP_RIGHT_US - (int)g_motor_delta_limit;
  const int right_max = SERVO_STOP_RIGHT_US + (int)g_motor_delta_limit;

  if (value_us < left_min && value_us < right_min) {
    return (left_min > right_min) ? left_min : right_min;
  }

  if (value_us > left_max && value_us > right_max) {
    return (left_max < right_max) ? left_max : right_max;
  }

  return value_us;
}

/**
 * @brief Sets wheel pulse widths using safe constrained values.
 *
 * Stores the last applied wheel values for later verbose/debug reporting.
 *
 * @param[in]  left_us Requested left wheel pulse width
 * @param[in]  right_us Requested right wheel pulse width
 * @param[out] none
 * @return     void
 */
inline void setWheels(int left_us = SERVO_STOP_LEFT_US,
                      int right_us = SERVO_STOP_RIGHT_US) {
  const int safe_left  = constrain(left_us,
                                   SERVO_STOP_LEFT_US - (int)g_motor_delta_limit,
                                   SERVO_STOP_LEFT_US + (int)g_motor_delta_limit);

  const int safe_right = constrain(right_us,
                                   SERVO_STOP_RIGHT_US - (int)g_motor_delta_limit,
                                   SERVO_STOP_RIGHT_US + (int)g_motor_delta_limit);

  const int applied_left = g_last_left_us + constrain(safe_left - g_last_left_us,
                                                       -MOTOR_RAMP_STEP_US,
                                                       MOTOR_RAMP_STEP_US);

  const int applied_right = g_last_right_us + constrain(safe_right - g_last_right_us,
                                                         -MOTOR_RAMP_STEP_US,
                                                         MOTOR_RAMP_STEP_US);

  g_left_wheel.writeMicroseconds(applied_left);
  g_right_wheel.writeMicroseconds(applied_right);

  g_last_left_us = applied_left;
  g_last_right_us = applied_right;

  delay(2);
}

/**
 * @brief Stops both wheels.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void stopWheels() {
  setWheels(SERVO_STOP_LEFT_US, SERVO_STOP_RIGHT_US);
}

/**
 * @brief Writes raw LED values to both LEDs.
 *
 * @param[in]  left_value Raw left LED value
 * @param[in]  right_value Raw right LED value
 * @param[out] none
 * @return     void
 */
inline void setLedRaw(uint8_t left_value, uint8_t right_value) {
  digitalWrite(PIN_LED_LEFT, left_value);
  digitalWrite(PIN_LED_RIGHT, right_value);
}

/**
 * @brief Reads the logical state of one LED.
 *
 * @param[in]  led_id LED identifier
 * @param[out] none
 * @return     LED_STATE_ON or LED_STATE_OFF
 */
inline uint8_t getLedStateById(uint8_t led_id) {
  uint8_t pin = PIN_LED_LEFT;

  if (led_id == LED_ID_RIGHT) {
    pin = PIN_LED_RIGHT;
  }

  return (digitalRead(pin) == LED_ON) ? LED_STATE_ON : LED_STATE_OFF;
}

/**
 * @brief Sets one or both LEDs by logical LED identifier.
 *
 * @param[in]  led_id LED identifier
 * @param[in]  state Requested LED state
 * @param[out] none
 * @return     void
 */
inline void setLedById(uint8_t led_id, uint8_t state) {
  const uint8_t pin_value = (state == LED_STATE_ON) ? LED_ON : LED_OFF;

  if (led_id == LED_ID_LEFT || led_id == LED_ID_BOTH) {
    digitalWrite(PIN_LED_LEFT, pin_value);
  }

  if (led_id == LED_ID_RIGHT || led_id == LED_ID_BOTH) {
    digitalWrite(PIN_LED_RIGHT, pin_value);
  }
}

/**
 * @brief Applies SET_LED semantics using LED id, mode, and state.
 *
 * Supported modes:
 * - LED_MODE_WRITE  : write the requested state directly
 * - LED_MODE_TOGGLE : toggle the selected LED output(s)
 *
 * @param[in]  led_id LED identifier
 * @param[in]  led_mode LED mode
 * @param[in]  led_state Requested LED state for write mode
 * @param[out] applied_state Resulting logical state after the operation
 * @return     true if arguments were accepted, false otherwise
 */
inline bool applyLedCommand(uint8_t led_id,
                            uint8_t led_mode,
                            uint8_t led_state,
                            uint8_t& applied_state) {
  if (led_id < LED_ID_LEFT || led_id > LED_ID_BOTH) {
    return false;
  }

  if (led_mode == LED_MODE_WRITE) {
    if (led_state != LED_STATE_OFF && led_state != LED_STATE_ON) {
      return false;
    }

    setLedById(led_id, led_state);
    applied_state = led_state;
    return true;
  }

  if (led_mode == LED_MODE_TOGGLE) {
    uint8_t current_state = LED_STATE_OFF;

    if (led_id == LED_ID_BOTH) {
      const bool left_on = (getLedStateById(LED_ID_LEFT) == LED_STATE_ON);
      const bool right_on = (getLedStateById(LED_ID_RIGHT) == LED_STATE_ON);
      current_state = (left_on && right_on) ? LED_STATE_ON : LED_STATE_OFF;
    } else {
      current_state = getLedStateById(led_id);
    }

    applied_state = (current_state == LED_STATE_ON) ? LED_STATE_OFF : LED_STATE_ON;
    setLedById(led_id, applied_state);
    return true;
  }

  return false;
}

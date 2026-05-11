#pragma once
#include <Arduino.h>
#include "Globals.h"
#include "Motion.h"
#include "Qti.h"
#include "Protocol.h"

/**
 * @file LineFollower.h
 * @brief Inline helpers for line following, mode changes, and marker handling.
 *
 * Sensor semantics used in this file:
 * - 1 = white background
 * - 0 = black line / black marker
 */

/**
 * @brief Checks whether all three logical sensor values indicate white.
 *
 * White background means the robot no longer sees the black line.
 *
 * @param[in]  l Left sensor logical value, 1 = white, 0 = black
 * @param[in]  m Middle sensor logical value, 1 = white, 0 = black
 * @param[in]  r Right sensor logical value, 1 = white, 0 = black
 * @param[out] none
 * @return     true if all sensors see white, false otherwise
 */
inline bool isAllWhite(bool l, bool m, bool r) {
  return l && m && r;
}

/**
 * @brief Checks whether all three logical sensor values indicate black.
 *
 * Used for marker / finish detection.
 *
 * @param[in]  l Left sensor logical value, 1 = white, 0 = black
 * @param[in]  m Middle sensor logical value, 1 = white, 0 = black
 * @param[in]  r Right sensor logical value, 1 = white, 0 = black
 * @param[out] none
 * @return     true if all sensors see black, false otherwise
 */
inline bool isAllBlack(bool l, bool m, bool r) {
  return (!l && !m && !r);
}

/**
 * @brief Checks whether all three QTI raw readings appear invalid.
 *
 * If all three readings remain at timeout value, sensor data is considered
 * unreliable and may indicate a sensor or wiring fault.
 *
 * @param[in]  tl Raw left QTI reading in microseconds
 * @param[in]  tm Raw middle QTI reading in microseconds
 * @param[in]  tr Raw right QTI reading in microseconds
 * @param[out] none
 * @return     true if all three sensors appear invalid, false otherwise
 */
inline bool qtiSensorsInvalid(unsigned int tl, unsigned int tm, unsigned int tr) {
  return (tl >= QTI_TIMEOUT_US) &&
         (tm >= QTI_TIMEOUT_US) &&
         (tr >= QTI_TIMEOUT_US);
}

/**
 * @brief Emits line visibility events with a short debounce.
 *
 * QTI readings can flicker at curve edges. Debouncing these events reduces
 * serial bursts without changing the actual line-following control state.
 *
 * @param[in]  event_code EV_LINE_LOST or EV_LINE_DETECTED
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
inline void sendLineVisibilityEvent(uint8_t event_code, unsigned long now) {
  if (now - g_last_line_event_ms < LINE_EVENT_MIN_GAP_MS) {
    return;
  }

  sendEvent(event_code);
  g_last_line_event_ms = now;
}

/**
 * @brief Emits one hard-turn event for the currently active curve.
 *
 * Event is emitted only when no previous hard-turn event is latched. The latch
 * is released after the robot has driven centered for several control steps.
 *
 * @param[in]  direction -1 for left, 1 for right
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
inline void emitHardTurnEventOnce(int8_t direction, unsigned long now) {
  if (direction == 0) {
    return;
  }

  if (g_last_turn_event_dir != 0) {
    return;
  }

  if (direction < 0) {
    sendEvent(EV_TURN_LEFT);
  } else {
    sendEvent(EV_TURN_RIGHT);
  }

  g_last_turn_event_dir = direction;
  g_last_turn_event_ms = now;
  g_centered_consec = 0;
}

/**
 * @brief Clears remembered hard-turn event state immediately.
 *
 * Timestamp is intentionally preserved for diagnostics / telemetry history.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void clearHardTurnEventState() {
  g_last_turn_event_dir = 0;
  g_centered_consec = 0;
}

/**
 * @brief Releases hard-turn event latch after stable centered driving.
 *
 * Soft steering is still treated as part of the same curve. A new hard-turn
 * event becomes possible only after enough centered forward steps.
 *
 * @param[in]  centered true when the robot is driving centered on the line
 * @param[out] none
 * @return     void
 */
inline void releaseHardTurnEventWhenCentered(bool centered) {
  if (g_last_turn_event_dir == 0) {
    g_centered_consec = 0;
    return;
  }

  if (!centered) {
    g_centered_consec = 0;
    return;
  }

  if (g_centered_consec < HARD_TURN_RELEASE_STEPS) {
    g_centered_consec++;
  }

  if (g_centered_consec >= HARD_TURN_RELEASE_STEPS) {
    clearHardTurnEventState();
  }
}

/**
 * @brief Sets LEDs according to steering direction.
 *
 * Rules:
 * - left turn  -> left LED on
 * - right turn -> right LED on
 * - straight   -> both LEDs off
 *
 * @param[in]  direction -1 for left, 1 for right, 0 for straight
 * @param[out] none
 * @return     void
 */
inline void setTurnLeds(int8_t direction) {
  if (direction < 0) {
    setLedRaw(LED_ON, LED_OFF);
    return;
  }

  if (direction > 0) {
    setLedRaw(LED_OFF, LED_ON);
    return;
  }

  setLedRaw(LED_OFF, LED_OFF);
}

/**
 * @brief Resets run-mode tracking state variables.
 *
 * Initializes timers, pauses, counters, and cooldowns used by the line
 * follower runtime when entering run mode.
 *
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
inline void resetRunTrackingState(unsigned long now) {
  g_start_countdown_active = true;
  g_start_begin_ms = now;

  g_start_boost_active = false;
  g_start_boost_begin_ms = 0;

  g_lap_pause_active = false;
  g_lap_pause_begin_ms = 0;

  g_marker_pause_active = false;
  g_marker_pause_begin_ms = 0;

  g_special_line_consec = 0;
  g_centered_consec = 0;
  g_special_line_armed = false;

  g_marker_counter = 0;
  g_finish_cooldown_until_ms = now + FINISH_COOLDOWN_MS;
  g_marker_cooldown_until_ms = now + MARKER_COOLDOWN_MS;

  g_line_lost_since_ms = 0;
  g_last_line_event_ms = 0;
  g_line_seen_last = true;
  g_off_track_reported = false;
  g_qti_fault_since_ms = 0;
  g_last_turn_event_dir = 0;
  g_last_turn_event_ms = 0;
}

/**
 * @brief Starts the run-mode initialization sequence.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void enterRunModeSequence() {
  const unsigned long now = millis();
  resetRunTrackingState(now);
}

/**
 * @brief Checks whether a mode transition is allowed.
 *
 * @param[in]  current_mode Current robot mode
 * @param[in]  new_mode Requested robot mode
 * @param[out] none
 * @return     true if the transition is allowed, false otherwise
 */
inline bool modeTransitionAllowed(RobotMode current_mode, RobotMode new_mode) {
  if (current_mode == new_mode) {
    return true;
  }

  switch (current_mode) {
    case MODE_IDLE:
      return (new_mode == MODE_RUN || new_mode == MODE_TEST || new_mode == MODE_ERROR);
    case MODE_RUN:
      return (new_mode == MODE_IDLE || new_mode == MODE_ERROR);
    case MODE_TEST:
      return (new_mode == MODE_IDLE || new_mode == MODE_ERROR);
    case MODE_ERROR:
      return (new_mode == MODE_IDLE);
    default:
      return false;
  }
}

/**
 * @brief Changes the robot mode and resets related runtime state.
 *
 * Sends a mode-changed event when the mode actually changes. When entering
 * run mode, also starts the run sequence and emits the app-start event.
 *
 * @param[in]  new_mode Requested robot mode
 * @param[out] none
 * @return     true if the mode was accepted, false otherwise
 */
inline bool setMode(RobotMode new_mode) {
  if (!modeTransitionAllowed(g_mode, new_mode)) {
    return false;
  }

  const bool changed = (g_mode != new_mode);
  g_mode = new_mode;

  if (changed) {
    sendEventData1(EV_MODE_CHANGED, (uint16_t)new_mode);
  }

  if (g_mode == MODE_RUN) {
    g_manual_drive_active = false;
    g_manual_drive_until_ms = 0;
    enterRunModeSequence();

    if (changed) {
      sendEvent(EV_APP_START);
    }
    return true;
  }

  stopWheels();
  setLedRaw(LED_OFF, LED_OFF);

  g_start_countdown_active = false;
  g_start_boost_active = false;
  g_lap_pause_active = false;
  g_marker_pause_active = false;
  g_special_line_consec = 0;
  g_centered_consec = 0;
  g_special_line_armed = false;
  g_marker_counter = 0;
  g_line_lost_since_ms = 0;
  g_last_line_event_ms = 0;
  g_off_track_reported = false;
  g_qti_fault_since_ms = 0;
  g_last_turn_event_dir = 0;

  g_manual_drive_active = false;
  g_manual_drive_until_ms = 0;

  return true;
}

/**
 * @brief Polls the user button and toggles run/idle mode on press.
 *
 * Applies a startup ignore time and a simple debounce delay.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void pollButton() {
  const unsigned long now = millis();
  const int current_button_state = digitalRead(PIN_BUTTON);

  if (now < g_button_ready_after_ms) {
    g_last_button_state = current_button_state;
    return;
  }

  if (g_last_button_state == HIGH && current_button_state == LOW) {
    sendEvent(EV_BUTTON_PRESSED);

    if (g_mode == MODE_RUN) {
      setMode(MODE_IDLE);
    } else if (g_mode == MODE_IDLE) {
      setMode(MODE_RUN);
    }

    delay(BUTTON_DEBOUNCE_MS);
  }

  g_last_button_state = current_button_state;
}

/**
 * @brief Starts the marker pause sequence.
 *
 * Increments the marker counter, sends a turn-ahead event, stops the wheels,
 * enables LEDs, and starts the cooldown timer.
 *
 * Marker is treated as a pre-turn indicator, therefore the event announces
 * that a turn is ahead instead of reporting a generic marker event.
 *
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
inline void beginMarkerPause(unsigned long now) {
  g_marker_counter++;
  sendEventData1(EV_APP_TURN_AHEAD, g_marker_counter);

  stopWheels();
  setLedRaw(LED_ON, LED_ON);

  g_marker_pause_active = true;
  g_marker_pause_begin_ms = now;
  g_marker_cooldown_until_ms = now + MARKER_COOLDOWN_MS;

  g_special_line_consec = 0;
  clearHardTurnEventState();
}

/**
 * @brief Starts the finish pause sequence.
 *
 * Stops the wheels, enables LEDs, and marks the finish pause as active.
 *
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
inline void beginFinishPause(unsigned long now) {
  sendEvent(EV_APP_FINISH);

  stopWheels();
  setLedRaw(LED_ON, LED_ON);

  g_lap_pause_active = true;
  g_lap_pause_begin_ms = now;

  g_special_line_consec = 0;
  clearHardTurnEventState();
}

/**
 * @brief Executes one line follower control step.
 *
 * Sensor logic used here:
 * - 1 = white
 * - 0 = black
 *
 * Therefore:
 * - all white  -> line lost / off-track candidate
 * - all black  -> marker / finish candidate
 *
 * Robot does not enter MODE_ERROR on line loss. It keeps searching for the
 * line. MODE_ERROR is reserved here for clear QTI sensor failure.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void lineFollowerStep() {
  const unsigned long now = millis();

  const unsigned int tl = readQtiTime(PIN_QTI_LEFT);
  const unsigned int tm = readQtiTime(PIN_QTI_MIDDLE);
  const unsigned int tr = readQtiTime(PIN_QTI_RIGHT);

  /**
   * Detect sensor failure separately from normal line loss.
   * If all three sensors sit at timeout long enough, data is likely invalid.
   */
  if (qtiSensorsInvalid(tl, tm, tr)) {
    if (g_qti_fault_since_ms == 0) {
      g_qti_fault_since_ms = now;
    }

    if (now - g_qti_fault_since_ms >= QTI_SENSOR_ERROR_MS) {
      sendEvent(EV_FAULT);
      setMode(MODE_ERROR);
      return;
    }
  } else {
    g_qti_fault_since_ms = 0;
  }

  /**
   * In this project:
   * - white = 1
   * - black = 0
   */
  const bool l = (tl < g_qti_threshold_us);
  const bool m = (tm < g_qti_threshold_us);
  const bool r = (tr < g_qti_threshold_us);

  const bool all_white = isAllWhite(l, m, r);
  const bool all_black = isAllBlack(l, m, r);

  /**
   * Line is considered visible when at least one sensor still sees black.
   * Since black = 0, line is visible when not all sensors are white.
   */
  const bool line_seen = !all_white;

  if (!line_seen && g_line_seen_last) {
    sendLineVisibilityEvent(EV_LINE_LOST, now);
    g_line_seen_last = false;
    g_line_lost_since_ms = now;
    g_off_track_reported = false;
  }

  if (line_seen && !g_line_seen_last) {
    sendLineVisibilityEvent(EV_LINE_DETECTED, now);
    g_line_seen_last = true;
    g_line_lost_since_ms = 0;
    g_off_track_reported = false;
  }

  /**
   * If line has been lost for long enough, report it as a fault/off-track.
   * Robot still keeps searching for the line and does not enter MODE_ERROR.
   */
  if (!line_seen && g_line_lost_since_ms != 0 && !g_off_track_reported) {
    if (now - g_line_lost_since_ms >= LINE_LOST_OFF_TRACK_MS) {
      sendEvent(EV_FAULT);
      sendEvent(EV_OFF_TRACK);
      g_off_track_reported = true;
    }
  }

  if (g_show_qti_values && (now - g_last_sensor_event_ms >= SENSOR_EVENT_MS)) {
    g_last_sensor_event_ms = now;
    sendSensorEvent((uint8_t)l, (uint8_t)m, (uint8_t)r, tl, tm, tr);
  }

  if (g_start_countdown_active) {
    stopWheels();
    setLedRaw(LED_ON, LED_ON);
    clearHardTurnEventState();

    if (now - g_start_begin_ms >= RUN_START_HOLD_MS) {
      g_start_countdown_active = false;
      g_start_boost_active = true;
      g_start_boost_begin_ms = now;
      setLedRaw(LED_OFF, LED_OFF);
      sendEvent(EV_APP_BOOST);
    }
    return;
  }

  if (g_start_boost_active) {
    setWheels(SPEED_FWD_LEFT_US, SPEED_FWD_RIGHT_US);
    setTurnLeds(0);
    clearHardTurnEventState();

    if (now - g_start_boost_begin_ms >= START_BOOST_MS) {
      g_start_boost_active = false;
      g_special_line_consec = 0;
    }
    return;
  }

  if (g_marker_pause_active) {
    stopWheels();
    setLedRaw(LED_ON, LED_ON);
    clearHardTurnEventState();

    if (now - g_marker_pause_begin_ms >= MARKER_PAUSE_MS) {
      g_marker_pause_active = false;
      setLedRaw(LED_OFF, LED_OFF);

      g_start_boost_active = true;
      g_start_boost_begin_ms = now;
    }
    return;
  }

  if (g_lap_pause_active) {
    stopWheels();
    setLedRaw(LED_ON, LED_ON);
    clearHardTurnEventState();

    if (now - g_lap_pause_begin_ms >= FINISH_PAUSE_MS) {
      g_lap_pause_active = false;
      setLedRaw(LED_OFF, LED_OFF);

      g_lap_counter++;
      sendLapEvent(g_lap_counter);

      g_marker_counter = 0;
      g_marker_cooldown_until_ms = now + MARKER_COOLDOWN_MS;
      g_finish_cooldown_until_ms = now + FINISH_COOLDOWN_MS;

      g_start_boost_active = true;
      g_start_boost_begin_ms = now;
    }
    return;
  }

  const bool can_detect_marker = (now >= g_marker_cooldown_until_ms);
  const bool can_detect_finish = (now >= g_finish_cooldown_until_ms);

  /**
   * All-black zone handling:
   * on marker / finish robot must keep driving forward and count duration.
   * It must NOT enter normal steering branches while all-black continues.
   */
  if (all_black) {
    if (g_special_line_consec < SPECIAL_LINE_CONSEC_MAX) {
      g_special_line_consec++;
    }

    setWheels(SPEED_FWD_LEFT_US, SPEED_FWD_RIGHT_US);
    setTurnLeds(0);
    clearHardTurnEventState();
    return;
  }

  /**
   * If robot just exited an all-black section, decide whether it was
   * a marker or a finish line according to duration.
   */
  if (g_special_line_consec > 0) {
    if ((g_special_line_consec >= FINISH_LINE_MIN_STEPS) && can_detect_finish) {
      beginFinishPause(now);
      return;
    }

    if ((g_special_line_consec >= SPECIAL_LINE_MIN_STEPS) && can_detect_marker) {
      beginMarkerPause(now);
      return;
    }

    g_special_line_consec = 0;
  }

  int left_us = SERVO_STOP_LEFT_US;
  int right_us = SERVO_STOP_RIGHT_US;
  int8_t hard_turn_direction = 0;
  int8_t led_direction = 0;
  bool centered_forward = false;

  /**
   * Steering decision table.
   *
   * Semantics:
   * - 1 = white
   * - 0 = black
   *
   * This means:
   * - 1 0 1  => center on black line => drive forward
   * - 0 1 1  => black on left        => steer left
   * - 1 1 0  => black on right       => steer right
   */

  if (l && m && r) {
    /**
     * All white: line temporarily lost.
     * Use previous direction to search for the line.
     * This is treated as a hard search turn.
     */
    if (g_last_dir >= 0) {
      left_us = SPEED_HARD_RIGHT_US_LEFT;
      right_us = SPEED_HARD_RIGHT_US_RIGHT;
      hard_turn_direction = 1;
      led_direction = 1;
    } else {
      left_us = SPEED_HARD_LEFT_US_LEFT;
      right_us = SPEED_HARD_LEFT_US_RIGHT;
      hard_turn_direction = -1;
      led_direction = -1;
    }
  } else if (!l && m && r) {
    /**
     * Left sensor sees black.
     * Hard left turn.
     */
    left_us = SPEED_HARD_LEFT_US_LEFT;
    right_us = SPEED_HARD_LEFT_US_RIGHT;
    g_last_dir = -1;
    hard_turn_direction = -1;
    led_direction = -1;
  } else if (l && m && !r) {
    /**
     * Right sensor sees black.
     * Hard right turn.
     */
    left_us = SPEED_HARD_RIGHT_US_LEFT;
    right_us = SPEED_HARD_RIGHT_US_RIGHT;
    g_last_dir = 1;
    hard_turn_direction = 1;
    led_direction = 1;
  } else if (l && !m && r) {
    /**
     * Middle sensor sees black.
     */
    left_us = SPEED_FWD_LEFT_US;
    right_us = SPEED_FWD_RIGHT_US;
    led_direction = 0;
    centered_forward = true;
  } else if (!l && !m && r) {
    /**
     * Left + middle see black.
     * Soft left turn.
     */
    left_us = SPEED_SOFT_LEFT_US_LEFT;
    right_us = SPEED_SOFT_LEFT_US_RIGHT;
    g_last_dir = -1;
    led_direction = -1;
  } else if (l && !m && !r) {
    /**
     * Middle + right see black.
     * Soft right turn.
     */
    left_us = SPEED_SOFT_RIGHT_US_LEFT;
    right_us = SPEED_SOFT_RIGHT_US_RIGHT;
    g_last_dir = 1;
    led_direction = 1;
  } else if (!l && m && !r) {
    /**
     * Left + right black while middle white.
     * Keep moving forward as a safe fallback.
     */
    left_us = SPEED_FWD_LEFT_US;
    right_us = SPEED_FWD_RIGHT_US;
    led_direction = 0;
  } else {
    /**
     * Fallback search behaviour.
     * Treated as a hard search turn.
     */
    if (g_last_dir >= 0) {
      left_us = SPEED_HARD_RIGHT_US_LEFT;
      right_us = SPEED_HARD_RIGHT_US_RIGHT;
      hard_turn_direction = 1;
      led_direction = 1;
    } else {
      left_us = SPEED_HARD_LEFT_US_LEFT;
      right_us = SPEED_HARD_LEFT_US_RIGHT;
      hard_turn_direction = -1;
      led_direction = -1;
    }
  }

  if (hard_turn_direction != 0) {
    emitHardTurnEventOnce(hard_turn_direction, now);
  } else {
    releaseHardTurnEventWhenCentered(centered_forward);
  }

  setTurnLeds(led_direction);
  setWheels(left_us, right_us);
}

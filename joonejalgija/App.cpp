#include <Arduino.h>
#include <avr/wdt.h>
#include "App.h"
#include "Config.h"
#include "Globals.h"
#include "Motion.h"
#include "Qti.h"
#include "Protocol.h"
#include "Parser.h"
#include "LineFollower.h"
#include "EEPROM_Settings.h"

/**
 * @file App.cpp
 * @brief Main application setup and loop implementation.
 */

/**
 * @brief Sends periodic verbose debug telemetry when enabled.
 *
 * In verbose mode robot sends additional application events containing:
 * - raw QTI sensor state and values
 * - averaged battery voltage
 * - last applied motor pulse widths
 *
 * Verbose output is rate-limited so the serial link is not flooded.
 *
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
static void sendVerboseIfDue(unsigned long now) {
  if (!g_debug_mode) {
    return;
  }

  if (now - g_last_debug_event_ms < VERBOSE_EVENT_MS) {
    return;
  }

  g_last_debug_event_ms = now;

  const unsigned int tl = readQtiTime(PIN_QTI_LEFT);
  const unsigned int tm = readQtiTime(PIN_QTI_MIDDLE);
  const unsigned int tr = readQtiTime(PIN_QTI_RIGHT);

  const uint8_t l = (tl < g_qti_threshold_us) ? 1 : 0;
  const uint8_t m = (tm < g_qti_threshold_us) ? 1 : 0;
  const uint8_t r = (tr < g_qti_threshold_us) ? 1 : 0;

  sendSensorEvent(l, m, r, tl, tm, tr);
  sendEventData1(EV_APP_BAT, readBatteryMv());
  sendEventData2(EV_APP_MOTOR, (uint16_t)g_last_left_us, (uint16_t)g_last_right_us);
}

/**
 * @brief Updates timed manual motor driving in idle/test modes.
 *
 * When a manual drive time was specified, wheels are stopped once the
 * timeout expires.
 *
 * @param[in]  now Current time in milliseconds
 * @param[out] none
 * @return     void
 */
static void updateManualDrive(unsigned long now) {
  if (!g_manual_drive_active) {
    stopWheels();
    return;
  }

  if (g_manual_drive_until_ms == 0) {
    return;
  }

  if (now >= g_manual_drive_until_ms) {
    g_manual_drive_active = false;
    g_manual_drive_until_ms = 0;
    stopWheels();
  }
}

/**
 * @brief Initializes the application, hardware, and runtime state.
 *
 * Configures serial communication, GPIO pins, servos, internal state,
 * battery input, periodic timers, and loads persistent settings from
 * EEPROM. Sends the initial reset event and first status frame.
 * Optionally enables the watchdog.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void appSetup() {
  MCUSR = 0;
  wdt_disable();

  Serial.begin(SERIAL_BAUD);

  pinMode(PIN_LED_RIGHT, OUTPUT);
  pinMode(PIN_LED_LEFT, OUTPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_BATTERY, INPUT);

  g_left_wheel.attach(PIN_SERVO_LEFT);
  g_right_wheel.attach(PIN_SERVO_RIGHT);

  stopWheels();
  setLedRaw(LED_ON, LED_ON);
  delay(BOOT_BLINK_MS);
  setLedRaw(LED_OFF, LED_OFF);

  g_mode = MODE_IDLE;
  g_start_countdown_active = false;
  g_start_boost_active = false;
  g_lap_pause_active = false;
  g_marker_pause_active = false;
  g_show_qti_values = 0;
  g_marker_counter = 0;
  g_special_line_consec = 0;
  g_centered_consec = 0;
  g_special_line_armed = false;
  g_line_lost_since_ms = 0;
  g_manual_drive_active = false;
  g_manual_drive_until_ms = 0;

  eepromLoadSettings();

  g_last_button_state = digitalRead(PIN_BUTTON);
  g_button_ready_after_ms = millis() + BUTTON_STARTUP_IGNORE_MS;

  g_last_status_ms = millis();
  g_last_step_ms = millis();
  g_last_sensor_event_ms = millis();
  g_last_debug_event_ms = millis();

  stopWheels();
  setLedRaw(LED_OFF, LED_OFF);

  sendEvent(EV_RESET);
  sendStatus();

  if (WATCHDOG_ENABLED) {
    wdt_enable(WDTO_1S);
  }
}

/**
 * @brief Runs one iteration of the main application loop.
 *
 * Services the watchdog, polls incoming commands, polls the user button,
 * sends periodic status frames, optionally sends verbose debug telemetry,
 * and executes the line follower state machine while the robot is in run
 * mode.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void appLoop() {
  if (WATCHDOG_ENABLED) {
    wdt_reset();
  }

  pollCommands();
  pollButton();

  const unsigned long now = millis();

  if (g_telemetry_enabled && (now - g_last_status_ms >= STATUS_INTERVAL_MS)) {
    g_last_status_ms = now;
    sendStatus();
  }

  sendVerboseIfDue(now);

  if (g_mode == MODE_RUN) {
    if (now - g_last_step_ms >= STEP_INTERVAL_MS) {
      g_last_step_ms = now;
      lineFollowerStep();
    }
  } else if (g_mode == MODE_TEST || g_mode == MODE_IDLE) {
    updateManualDrive(now);
  } else {
    stopWheels();
  }
}
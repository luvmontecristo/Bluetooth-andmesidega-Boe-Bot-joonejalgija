#pragma once
#include <Arduino.h>
#include "Globals.h"
#include "Protocol.h"
#include "Qti.h"
#include "Motion.h"
#include "LineFollower.h"
#include "EEPROM_Settings.h"

/**
 * @file Parser.h
 * @brief Inline command parsing and command handling logic.
 */

/**
 * @brief Parses a signed integer from a C string.
 *
 * @param[in]  s Null-terminated numeric string
 * @param[out] none
 * @return     Parsed integer value
 */
inline int parseIntSafe(const char* s) {
  int value = 0;
  int index = 0;
  bool negative = false;

  if (s[0] == '-') {
    negative = true;
    index = 1;
  }

  while (s[index] >= '0' && s[index] <= '9') {
    value = value * 10 + (s[index] - '0');
    index++;
  }

  return negative ? -value : value;
}

/**
 * @brief Checks whether a token contains a valid signed integer.
 *
 * @param[in]  s Null-terminated token string
 * @param[out] none
 * @return     true if the token is numeric, false otherwise
 */
inline bool isNumericToken(const char* s) {
  if (s[0] == '\0') {
    return false;
  }

  uint8_t i = 0;
  if (s[i] == '-') {
    i++;
  }

  bool has_digit = false;
  while (s[i] != '\0') {
    if (s[i] < '0' || s[i] > '9') {
      return false;
    }
    has_digit = true;
    i++;
  }

  return has_digit;
}

/**
 * @brief Compares two strings for equality.
 *
 * @param[in]  a First string
 * @param[in]  b Second string
 * @param[out] none
 * @return     true if strings are equal, false otherwise
 */
inline bool streq(const char* a, const char* b) {
  uint8_t i = 0;
  while (true) {
    if (a[i] != b[i]) {
      return false;
    }
    if (a[i] == '\0') {
      return true;
    }
    i++;
    if (i >= RX_BUF_SIZE) {
      return false;
    }
  }
}

/**
 * @brief Extracts the next token from a semicolon-separated string.
 *
 * @param[in]  src Source string
 * @param[in]  start Start index in source string
 * @param[out] out Destination buffer for the token
 * @param[in]  out_size Size of destination buffer
 * @return     Index of the next token start, end index, or -1 on error
 */
inline int nextToken(const char* src, int start, char* out, uint8_t out_size) {
  uint8_t j = 0;
  int i = start;

  while (src[i] != '\0' && src[i] != ';' && j < (out_size - 1)) {
    out[j++] = src[i++];
  }
  out[j] = '\0';

  if (src[i] == ';') {
    return i + 1;
  }

  if (src[i] == '\0') {
    return i;
  }

  return -1;
}

/**
 * @brief Checks whether an integer corresponds to a defined robot mode.
 *
 * @param[in]  value Integer mode value
 * @param[out] none
 * @return     true if the mode exists, false otherwise
 */
inline bool modeExists(int value) {
  return value >= (int)MODE_RUN && value <= (int)MODE_ERROR;
}

/**
 * @brief Checks whether a command code exists in the protocol.
 *
 * @param[in]  cmd_code Command code
 * @param[out] none
 * @return     true if the command exists, false otherwise
 */
inline bool commandExists(uint16_t cmd_code) {
  switch (cmd_code) {
    case CMD_PING:
    case CMD_MEMORY_DUMP:
    case CMD_SET_LED:
    case CMD_SET_TELEMETRY:
    case CMD_SET_DEBUG_MODE:
    case CMD_SET_MODE:
    case CMD_SET_MOTOR:
    case CMD_REDUCE_MAX_SPEED:
    case CMD_SET_QTI_THRESHOLD:
    case CMD_CHANGE_ROBOT_ID:
    case CMD_RESET_EEPROM:
    case CMD_GET_STATUS:
    case CMD_START_APP:
    case CMD_STOP_APP:
    case CMD_SHOW_QTI_VALUES:
    case CMD_SET_MAP_NUMBER:
    case CMD_TEST_DATA_DUMP:
    case CMD_TEST_READ_QTI:
    case CMD_TEST_READ_BAT:
    case CMD_TEST_ULTRA_SWEEP:
    case CMD_TEST_ULTRASOUND:
    case CMD_TEST_RFID_VALUE:
    case CMD_TEST_MOTOR_VALUE:
      return true;

    default:
      return false;
  }
}

/**
 * @brief Checks whether a command is allowed in the current robot mode.
 *
 * @param[in]  cmd_code Command code
 * @param[out] none
 * @return     true if the command is allowed, false otherwise
 */
inline bool commandAllowedInCurrentMode(uint16_t cmd_code) {
  switch (cmd_code) {
    case CMD_PING:
    case CMD_MEMORY_DUMP:
    case CMD_SET_DEBUG_MODE:
    case CMD_SET_MODE:
    case CMD_GET_STATUS:
    case CMD_START_APP:
    case CMD_STOP_APP:
      return true;

    case CMD_SET_TELEMETRY:
      return (g_mode != MODE_ERROR);

    case CMD_SHOW_QTI_VALUES:
      return (g_mode == MODE_IDLE || g_mode == MODE_TEST || g_mode == MODE_RUN);

    case CMD_SET_LED:
    case CMD_SET_MOTOR:
    case CMD_REDUCE_MAX_SPEED:
    case CMD_SET_QTI_THRESHOLD:
    case CMD_CHANGE_ROBOT_ID:
    case CMD_RESET_EEPROM:
    case CMD_SET_MAP_NUMBER:
      return (g_mode == MODE_TEST || g_mode == MODE_IDLE);

    case CMD_TEST_DATA_DUMP:
    case CMD_TEST_READ_QTI:
    case CMD_TEST_READ_BAT:
    case CMD_TEST_ULTRA_SWEEP:
    case CMD_TEST_ULTRASOUND:
    case CMD_TEST_RFID_VALUE:
    case CMD_TEST_MOTOR_VALUE:
      return (g_mode == MODE_TEST);

    default:
      return false;
  }
}

/**
 * @brief Handles the SET_LED command.
 *
 * Command format:
 * robot_id;2;3;led_id;led_mode;led_state
 *
 * @param[in]  arg1 LED identifier string
 * @param[in]  arg2 LED mode string
 * @param[in]  arg3 LED state string
 * @param[out] none
 * @return     void
 */
inline void handleSetLed(const char* arg1, const char* arg2, const char* arg3) {
  if (!isNumericToken(arg1) || !isNumericToken(arg2) || !isNumericToken(arg3)) {
    sendFault(FAULT_BAD_ARG);
    return;
  }

  const int led_id = parseIntSafe(arg1);
  const int led_mode = parseIntSafe(arg2);
  const int led_state = parseIntSafe(arg3);

  uint8_t applied_state = LED_STATE_OFF;
  if (!applyLedCommand((uint8_t)led_id,
                       (uint8_t)led_mode,
                       (uint8_t)led_state,
                       applied_state)) {
    sendFault(FAULT_BAD_ARG);
    return;
  }

  sendResponseData3(CMD_SET_LED,
                    (uint16_t)led_id,
                    (uint16_t)led_mode,
                    (uint16_t)applied_state);
}

/**
 * @brief Handles the SET_MOTOR command.
 *
 * Command format:
 * robot_id;2;7;left_us;right_us;drive_time_ms
 *
 * If drive_time_ms is zero, manual drive remains active until another
 * action changes the wheels or mode.
 *
 * @param[in]  arg1 Left motor pulse width string
 * @param[in]  arg2 Right motor pulse width string
 * @param[in]  arg3 Drive time in milliseconds
 * @param[out] none
 * @return     void
 */
inline void handleSetMotor(const char* arg1, const char* arg2, const char* arg3) {
  if (!isNumericToken(arg1) || !isNumericToken(arg2) || !isNumericToken(arg3)) {
    sendFault(FAULT_BAD_ARG);
    return;
  }

  const int left_us = parseIntSafe(arg1);
  const int right_us = parseIntSafe(arg2);
  const int drive_time_ms = parseIntSafe(arg3);

  if (drive_time_ms < 0) {
    sendFault(FAULT_BAD_ARG);
    return;
  }

  g_manual_left_us = left_us;
  g_manual_right_us = right_us;

  setWheels(g_manual_left_us, g_manual_right_us);

  g_manual_drive_active = true;
  if (drive_time_ms == 0) {
    g_manual_drive_until_ms = 0;
  } else {
    g_manual_drive_until_ms = millis() + (unsigned long)drive_time_ms;
  }

  sendResponseData3(CMD_SET_MOTOR,
                    (uint16_t)g_last_left_us,
                    (uint16_t)g_last_right_us,
                    (uint16_t)drive_time_ms);
}

/**
 * @brief Handles a decoded command and its arguments.
 *
 * @param[in]  cmd_code Command code
 * @param[in]  arg1 First command argument
 * @param[in]  arg2 Second command argument
 * @param[in]  arg3 Third command argument
 * @param[out] none
 * @return     void
 */
inline void handleCommand(uint16_t cmd_code,
                          const char* arg1,
                          const char* arg2,
                          const char* arg3) {
  if (!commandExists(cmd_code)) {
    sendFault(FAULT_UNKNOWN_CMD);
    return;
  }

  if (!commandAllowedInCurrentMode(cmd_code)) {
    sendFault(FAULT_NOT_ALLOWED);
    return;
  }

  switch (cmd_code) {
    case CMD_PING:
      sendResponse(CMD_PING);
      return;

    case CMD_MEMORY_DUMP:
      sendResponseData4(CMD_MEMORY_DUMP,
                        g_robot_id,
                        g_map_number,
                        g_motor_delta_limit,
                        g_qti_threshold_us);
      return;

    case CMD_SET_LED:
      handleSetLed(arg1, arg2, arg3);
      return;

    case CMD_SET_TELEMETRY:
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      g_telemetry_enabled = (parseIntSafe(arg1) == 0) ? 0 : 1;
      sendResponseData1(CMD_SET_TELEMETRY, g_telemetry_enabled);
      return;

    case CMD_SET_DEBUG_MODE:
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      g_debug_mode = (parseIntSafe(arg1) == 0) ? 0 : 1;
      sendResponseData1(CMD_SET_DEBUG_MODE, g_debug_mode);
      return;

    case CMD_SET_MODE: {
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      const int new_mode = parseIntSafe(arg1);
      if (!modeExists(new_mode)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      if (!setMode((RobotMode)new_mode)) {
        sendFault(FAULT_BAD_MODE);
        return;
      }

      sendResponseData1(CMD_SET_MODE, (uint16_t)new_mode);
      return;
    }

    case CMD_SET_MOTOR:
      handleSetMotor(arg1, arg2, arg3);
      return;

    case CMD_REDUCE_MAX_SPEED: {
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      int new_limit = parseIntSafe(arg1);
      new_limit = constrain(new_limit, MOTOR_DELTA_MIN, MOTOR_DELTA_MAX);

      eepromSetMaxSpeed((uint8_t)new_limit);
      sendResponseData1(CMD_REDUCE_MAX_SPEED, g_motor_delta_limit);
      return;
    }

    case CMD_SET_QTI_THRESHOLD: {
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      int threshold = parseIntSafe(arg1);
      threshold = constrain(threshold, QTI_THRESHOLD_MIN, QTI_THRESHOLD_MAX);

      eepromSetQtiThreshold((uint16_t)threshold);
      sendResponseData1(CMD_SET_QTI_THRESHOLD, g_qti_threshold_us);
      return;
    }

    case CMD_CHANGE_ROBOT_ID: {
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      int new_id = parseIntSafe(arg1);
      new_id = constrain(new_id, 1, 255);

      if (!eepromSetRobotId((uint8_t)new_id)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      sendResponseData1(CMD_CHANGE_ROBOT_ID, g_robot_id);
      return;
    }

    case CMD_RESET_EEPROM:
      eepromResetValues();
      sendResponse(CMD_RESET_EEPROM);
      return;

    case CMD_GET_STATUS:
      sendStatus();
      sendResponse(CMD_GET_STATUS);
      return;

    case CMD_START_APP:
      if (!setMode(MODE_RUN)) {
        sendFault(FAULT_BAD_MODE);
        return;
      }
      sendResponse(CMD_START_APP);
      return;

    case CMD_STOP_APP:
      if (!setMode(MODE_IDLE)) {
        sendFault(FAULT_BAD_MODE);
        return;
      }
      sendResponse(CMD_STOP_APP);
      return;

    case CMD_SHOW_QTI_VALUES:
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      g_show_qti_values = (parseIntSafe(arg1) == 0) ? 0 : 1;
      sendResponseData1(CMD_SHOW_QTI_VALUES, g_show_qti_values);
      return;

    case CMD_SET_MAP_NUMBER: {
      if (!isNumericToken(arg1)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      int new_map = parseIntSafe(arg1);
      new_map = constrain(new_map, 1, 255);

      if (!eepromSetMapNumber((uint8_t)new_map)) {
        sendFault(FAULT_BAD_ARG);
        return;
      }

      sendResponseData1(CMD_SET_MAP_NUMBER, g_map_number);
      return;
    }

    case CMD_TEST_DATA_DUMP: {
      const unsigned int tl = readQtiTime(PIN_QTI_LEFT);
      const unsigned int tm = readQtiTime(PIN_QTI_MIDDLE);
      const unsigned int tr = readQtiTime(PIN_QTI_RIGHT);

      sendResponseData3(CMD_TEST_READ_QTI, tl, tm, tr);
      sendResponseData1(CMD_TEST_READ_BAT, readBatteryMv());
      sendResponseData3(CMD_TEST_ULTRA_SWEEP, 0, 0, 0);
      sendResponseData1(CMD_TEST_ULTRASOUND, 0);
      sendResponseData1(CMD_TEST_RFID_VALUE, 0);
      sendResponseData2(CMD_TEST_MOTOR_VALUE,
                        (uint16_t)g_last_left_us,
                        (uint16_t)g_last_right_us);
      return;
    }

    case CMD_TEST_READ_QTI: {
      const unsigned int tl = readQtiTime(PIN_QTI_LEFT);
      const unsigned int tm = readQtiTime(PIN_QTI_MIDDLE);
      const unsigned int tr = readQtiTime(PIN_QTI_RIGHT);

      sendResponseData3(CMD_TEST_READ_QTI, tl, tm, tr);
      return;
    }

    case CMD_TEST_READ_BAT:
      sendResponseData1(CMD_TEST_READ_BAT, readBatteryMv());
      return;

    case CMD_TEST_ULTRA_SWEEP:
      sendResponseData3(CMD_TEST_ULTRA_SWEEP, 0, 0, 0);
      return;

    case CMD_TEST_ULTRASOUND:
      sendResponseData1(CMD_TEST_ULTRASOUND, 0);
      return;

    case CMD_TEST_RFID_VALUE:
      sendResponseData1(CMD_TEST_RFID_VALUE, 0);
      return;

    case CMD_TEST_MOTOR_VALUE:
      sendResponseData2(CMD_TEST_MOTOR_VALUE,
                        (uint16_t)g_last_left_us,
                        (uint16_t)g_last_right_us);
      return;

    default:
      sendFault(FAULT_UNKNOWN_CMD);
      return;
  }
}

/**
 * @brief Parses and handles one received command line.
 *
 * @param[in]  line Null-terminated input line buffer
 * @param[out] none
 * @return     void
 */
inline void handleLine(char* line) {
  char tok1[12];
  char tok2[12];
  char tok3[16];
  char tok4[16];
  char tok5[16];
  char tok6[16];

  int i = 0;
  i = nextToken(line, i, tok1, sizeof(tok1));
  if (i < 0) { sendFault(FAULT_BAD_ARG); return; }

  i = nextToken(line, i, tok2, sizeof(tok2));
  if (i < 0) { sendFault(FAULT_BAD_ARG); return; }

  i = nextToken(line, i, tok3, sizeof(tok3));
  if (i < 0) { sendFault(FAULT_BAD_ARG); return; }

  i = nextToken(line, i, tok4, sizeof(tok4));
  if (i < 0) { tok4[0] = '\0'; }

  i = nextToken(line, i, tok5, sizeof(tok5));
  if (i < 0) { tok5[0] = '\0'; }

  i = nextToken(line, i, tok6, sizeof(tok6));
  if (i < 0) { tok6[0] = '\0'; }

  if (!isNumericToken(tok1) || !isNumericToken(tok2)) {
    sendFault(FAULT_BAD_ARG);
    return;
  }

  const int target_robot_id = parseIntSafe(tok1);
  const int message_type = parseIntSafe(tok2);

  if (target_robot_id != (int)g_robot_id) {
    return;
  }

  if (message_type != (int)MSG_COMMAND) {
    sendFault(FAULT_BAD_ARG);
    return;
  }

  if (isNumericToken(tok3)) {
    handleCommand((uint16_t)parseIntSafe(tok3), tok4, tok5, tok6);
    return;
  }

  if (streq(tok3, "PING")) {
    handleCommand(CMD_PING, "", "", "");
    return;
  }

  if (streq(tok3, "STATUS")) {
    handleCommand(CMD_GET_STATUS, "", "", "");
    return;
  }

  if (streq(tok3, "START")) {
    handleCommand(CMD_START_APP, "", "", "");
    return;
  }

  if (streq(tok3, "STOP")) {
    handleCommand(CMD_STOP_APP, "", "", "");
    return;
  }

  if (streq(tok3, "MODE")) {
    handleCommand(CMD_SET_MODE, tok4, "", "");
    return;
  }

  sendFault(FAULT_UNKNOWN_CMD);
}

/**
 * @brief Polls serial input and processes completed command lines.
 *
 * Builds a line buffer from serial input. When a line ending is received,
 * the buffered line is parsed and handled. If the receive buffer overflows,
 * a bad-argument fault is sent and the buffer is cleared.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void pollCommands() {
  while (Serial.available()) {
    const char c = (char)Serial.read();

    if (c == '\n' || c == '\r') {
      if (g_rx_len == 0) {
        continue;
      }

      g_rx_buf[g_rx_len] = '\0';
      handleLine(g_rx_buf);
      g_rx_len = 0;
      continue;
    }

    if (g_rx_len < (RX_BUF_SIZE - 1)) {
      g_rx_buf[g_rx_len++] = c;
    } else {
      g_rx_len = 0;
      sendFault(FAULT_BAD_ARG);
    }
  }
}
#include "EEPROM_Settings.h"

#include <EEPROM.h>

#include "Globals.h"
#include "Config.h"

/**
 * @file EEPROM_Settings.cpp
 * @brief EEPROM-backed persistent settings implementation.
 */

/**
 * @brief EEPROM address map.
 *
 * Layout aligned with the protocol appendix as closely as possible while
 * keeping QTI threshold as uint16_t:
 * - 0x00 robot ID
 * - 0x01 max speed
 * - 0x02..0x03 QTI threshold
 * - 0x04 map number
 */
static const int ADDR_ROBOT_ID      = 0x00;
static const int ADDR_MAX_SPEED     = 0x01;
static const int ADDR_QTI_THRESHOLD = 0x02;
static const int ADDR_MAP_NUMBER    = 0x04;

/**
 * @brief Checks whether a robot ID is valid.
 *
 * A valid robot ID cannot be zero and cannot be 0xFF.
 *
 * @param[in]  id Robot ID to validate
 * @param[out] none
 * @return     true if the ID is valid, false otherwise
 */
static bool validRobotId(uint8_t id) {
  return id != 0 && id != 0xFF;
}

/**
 * @brief Checks whether a map number is valid.
 *
 * A valid map number cannot be zero and cannot be 0xFF.
 *
 * @param[in]  map_number Map number to validate
 * @param[out] none
 * @return     true if the map number is valid, false otherwise
 */
static bool validMapNumber(uint8_t map_number) {
  return map_number != 0 && map_number != 0xFF;
}

/**
 * @brief Clamps the maximum speed value to the configured valid range.
 *
 * @param[in]  value Requested maximum speed value
 * @param[out] none
 * @return     Clamped maximum speed value
 */
static uint8_t clampMaxSpeed(uint8_t value) {
  if (value > MOTOR_DELTA_MAX) {
    return MOTOR_DELTA_MAX;
  }
  return value;
}

/**
 * @brief Clamps the QTI threshold to the configured valid range.
 *
 * @param[in]  value Requested QTI threshold value
 * @param[out] none
 * @return     Clamped QTI threshold value
 */
static uint16_t clampQtiThreshold(uint16_t value) {
  if (value < QTI_THRESHOLD_MIN) {
    return QTI_THRESHOLD_MIN;
  }
  if (value > QTI_THRESHOLD_MAX) {
    return QTI_THRESHOLD_MAX;
  }
  return value;
}

/**
 * @brief Checks whether EEPROM appears to be uninitialized.
 *
 * Without a magic byte, EEPROM is treated as empty only when all relevant
 * fields still contain erased values.
 *
 * @param[in]  none
 * @param[out] none
 * @return     true if EEPROM appears empty, false otherwise
 */
static bool eepromLooksUninitialized() {
  uint16_t threshold = 0xFFFF;
  EEPROM.get(ADDR_QTI_THRESHOLD, threshold);

  return (EEPROM.read(ADDR_ROBOT_ID) == 0xFF) &&
         (EEPROM.read(ADDR_MAX_SPEED) == 0xFF) &&
         (EEPROM.read(ADDR_MAP_NUMBER) == 0xFF) &&
         (threshold == 0xFFFF);
}

/**
 * @brief Writes default settings to EEPROM.
 *
 * Stores default values for robot ID, maximum speed, QTI threshold,
 * and map number.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void eepromSaveDefaults() {
  EEPROM.update(ADDR_ROBOT_ID, ROBOT_ID_DEFAULT);
  EEPROM.update(ADDR_MAX_SPEED, MOTOR_DELTA_DEFAULT);

  const uint16_t default_qti = QTI_THRESHOLD_DEFAULT;
  EEPROM.put(ADDR_QTI_THRESHOLD, default_qti);

  EEPROM.update(ADDR_MAP_NUMBER, MAP_NUMBER_DEFAULT);
}

/**
 * @brief Resets EEPROM-backed settings to defaults and reloads globals.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void eepromResetValues() {
  eepromSaveDefaults();
  eepromLoadSettings();
}

/**
 * @brief Reads the robot ID from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Valid robot ID or default robot ID
 */
uint8_t eepromGetRobotId() {
  const uint8_t id = EEPROM.read(ADDR_ROBOT_ID);

  if (!validRobotId(id)) {
    return ROBOT_ID_DEFAULT;
  }

  return id;
}

/**
 * @brief Reads the map number from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Valid map number or default map number
 */
uint8_t eepromGetMapNumber() {
  const uint8_t map_number = EEPROM.read(ADDR_MAP_NUMBER);

  if (!validMapNumber(map_number)) {
    return MAP_NUMBER_DEFAULT;
  }

  return map_number;
}

/**
 * @brief Reads the maximum speed from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Valid maximum speed or default speed
 */
uint8_t eepromGetMaxSpeed() {
  const uint8_t value = EEPROM.read(ADDR_MAX_SPEED);

  if (value == 0xFF) {
    return MOTOR_DELTA_DEFAULT;
  }

  return clampMaxSpeed(value);
}

/**
 * @brief Reads the QTI threshold from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Valid QTI threshold or default threshold
 */
uint16_t eepromGetQtiThreshold() {
  uint16_t value = 0xFFFF;
  EEPROM.get(ADDR_QTI_THRESHOLD, value);

  if (value == 0xFFFF) {
    return QTI_THRESHOLD_DEFAULT;
  }

  return clampQtiThreshold(value);
}

/**
 * @brief Stores a robot ID in EEPROM and updates the runtime global.
 *
 * @param[in]  id New robot ID
 * @param[out] none
 * @return     true if the ID was accepted, false otherwise
 */
bool eepromSetRobotId(uint8_t id) {
  if (!validRobotId(id)) {
    return false;
  }

  EEPROM.update(ADDR_ROBOT_ID, id);
  g_robot_id = id;
  return true;
}

/**
 * @brief Stores a map number in EEPROM and updates the runtime global.
 *
 * @param[in]  map_number New map number
 * @param[out] none
 * @return     true if the map number was accepted, false otherwise
 */
bool eepromSetMapNumber(uint8_t map_number) {
  if (!validMapNumber(map_number)) {
    return false;
  }

  EEPROM.update(ADDR_MAP_NUMBER, map_number);
  g_map_number = map_number;
  return true;
}

/**
 * @brief Stores a maximum speed value in EEPROM and updates the runtime global.
 *
 * @param[in]  speed New maximum speed
 * @param[out] none
 * @return     void
 */
void eepromSetMaxSpeed(uint8_t speed) {
  speed = clampMaxSpeed(speed);
  EEPROM.update(ADDR_MAX_SPEED, speed);
  g_motor_delta_limit = speed;
}

/**
 * @brief Stores a QTI threshold in EEPROM and updates the runtime global.
 *
 * @param[in]  threshold New QTI threshold
 * @param[out] none
 * @return     void
 */
void eepromSetQtiThreshold(uint16_t threshold) {
  threshold = clampQtiThreshold(threshold);
  EEPROM.put(ADDR_QTI_THRESHOLD, threshold);
  g_qti_threshold_us = threshold;
}

/**
 * @brief Loads settings from EEPROM and writes defaults if needed.
 *
 * If EEPROM appears uninitialized, default settings are written first.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void eepromLoadSettings() {
  if (eepromLooksUninitialized()) {
    eepromSaveDefaults();
  }

  g_robot_id = eepromGetRobotId();
  g_map_number = eepromGetMapNumber();
  g_motor_delta_limit = eepromGetMaxSpeed();
  g_qti_threshold_us = eepromGetQtiThreshold();
}
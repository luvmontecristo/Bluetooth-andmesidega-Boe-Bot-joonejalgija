#pragma once
#include <Arduino.h>

/**
 * @file EEPROM_Settings.h
 * @brief EEPROM access helpers for persistent robot settings.
 */

/**
 * @brief Loads all persistent settings from EEPROM into globals.
 *
 * If EEPROM looks uninitialized, default values are first written to EEPROM
 * and then loaded into runtime globals.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void eepromLoadSettings();

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
void eepromSaveDefaults();

/**
 * @brief Resets EEPROM-backed settings to defaults and reloads globals.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
void eepromResetValues();

/**
 * @brief Stores a new robot ID in EEPROM.
 *
 * Also updates the runtime robot ID global if the value is accepted.
 *
 * @param[in]  id New robot ID
 * @param[out] none
 * @return     true if the ID was accepted, false otherwise
 */
bool eepromSetRobotId(uint8_t id);

/**
 * @brief Stores a new map number in EEPROM.
 *
 * Also updates the runtime map number global if the value is accepted.
 *
 * @param[in]  map_number New map number
 * @param[out] none
 * @return     true if the map number was accepted, false otherwise
 */
bool eepromSetMapNumber(uint8_t map_number);

/**
 * @brief Stores a new maximum speed in EEPROM.
 *
 * Also updates the runtime motor speed limit global.
 *
 * @param[in]  speed New maximum speed value
 * @param[out] none
 * @return     void
 */
void eepromSetMaxSpeed(uint8_t speed);

/**
 * @brief Stores a new QTI threshold in EEPROM.
 *
 * Also updates the runtime QTI threshold global.
 *
 * @param[in]  threshold New QTI threshold
 * @param[out] none
 * @return     void
 */
void eepromSetQtiThreshold(uint16_t threshold);

/**
 * @brief Reads the robot ID from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Robot ID value or default robot ID if invalid
 */
uint8_t eepromGetRobotId();

/**
 * @brief Reads the map number from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Map number value or default map number if invalid
 */
uint8_t eepromGetMapNumber();

/**
 * @brief Reads the maximum speed from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     Maximum speed value or default value if EEPROM is empty
 */
uint8_t eepromGetMaxSpeed();

/**
 * @brief Reads the QTI threshold from EEPROM.
 *
 * @param[in]  none
 * @param[out] none
 * @return     QTI threshold value or default threshold if EEPROM is empty
 */
uint16_t eepromGetQtiThreshold();
#pragma once
#include <Arduino.h>
#include "Globals.h"
#include "Qti.h"
#include "ProtocolDefs.h"
#include "Config.h"

/**
 * @file Protocol.h
 * @brief Inline helpers for serial protocol output.
 */

/**
 * @brief Writes a protocol field separator to serial output.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void serialFieldSep() {
  Serial.print(';');
}

/**
 * @brief Writes the protocol line ending to serial output.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void serialLineEnd() {
  Serial.print("\r\n");
}

/**
 * @brief Sends the current status frame.
 *
 * @param[in]  none
 * @param[out] none
 * @return     void
 */
inline void sendStatus() {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_STATUS);
  serialFieldSep();
  Serial.print((int)g_status_seq);
  serialFieldSep();
  Serial.print((int)readBatteryMv());
  serialFieldSep();
  Serial.print((int)g_map_number);
  serialFieldSep();
  Serial.print((int)g_mode);
  serialFieldSep();
  Serial.print((int)PROTOCOL_V1);
  serialLineEnd();

  g_status_seq++;
}

/**
 * @brief Sends an event without payload.
 *
 * @param[in]  event_code Event code
 * @param[out] none
 * @return     void
 */
inline void sendEvent(uint8_t event_code) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_EVENT);
  serialFieldSep();
  Serial.print((int)event_code);
  serialLineEnd();
}

/**
 * @brief Sends an event with one payload field.
 *
 * @param[in]  event_code Event code
 * @param[in]  value1 First payload value
 * @param[out] none
 * @return     void
 */
inline void sendEventData1(uint8_t event_code, uint16_t value1) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_EVENT);
  serialFieldSep();
  Serial.print((int)event_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialLineEnd();
}

/**
 * @brief Sends an event with two payload fields.
 *
 * @param[in]  event_code Event code
 * @param[in]  value1 First payload value
 * @param[in]  value2 Second payload value
 * @param[out] none
 * @return     void
 */
inline void sendEventData2(uint8_t event_code, uint16_t value1, uint16_t value2) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_EVENT);
  serialFieldSep();
  Serial.print((int)event_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialFieldSep();
  Serial.print((int)value2);
  serialLineEnd();
}

/**
 * @brief Sends an event with six payload fields.
 *
 * @param[in]  event_code Event code
 * @param[in]  value1 First payload value
 * @param[in]  value2 Second payload value
 * @param[in]  value3 Third payload value
 * @param[in]  value4 Fourth payload value
 * @param[in]  value5 Fifth payload value
 * @param[in]  value6 Sixth payload value
 * @param[out] none
 * @return     void
 */
inline void sendEventData6(uint8_t event_code,
                           uint16_t value1,
                           uint16_t value2,
                           uint16_t value3,
                           uint16_t value4,
                           uint16_t value5,
                           uint16_t value6) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_EVENT);
  serialFieldSep();
  Serial.print((int)event_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialFieldSep();
  Serial.print((int)value2);
  serialFieldSep();
  Serial.print((int)value3);
  serialFieldSep();
  Serial.print((int)value4);
  serialFieldSep();
  Serial.print((int)value5);
  serialFieldSep();
  Serial.print((int)value6);
  serialLineEnd();
}

/**
 * @brief Sends a response without payload.
 *
 * @param[in]  cmd_code Command code
 * @param[out] none
 * @return     void
 */
inline void sendResponse(uint16_t cmd_code) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_RESPONSE);
  serialFieldSep();
  Serial.print((int)cmd_code);
  serialLineEnd();
}

/**
 * @brief Sends a response with one payload field.
 *
 * @param[in]  cmd_code Command code
 * @param[in]  value1 First payload value
 * @param[out] none
 * @return     void
 */
inline void sendResponseData1(uint16_t cmd_code, uint16_t value1) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_RESPONSE);
  serialFieldSep();
  Serial.print((int)cmd_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialLineEnd();
}

/**
 * @brief Sends a response with two payload fields.
 *
 * @param[in]  cmd_code Command code
 * @param[in]  value1 First payload value
 * @param[in]  value2 Second payload value
 * @param[out] none
 * @return     void
 */
inline void sendResponseData2(uint16_t cmd_code, uint16_t value1, uint16_t value2) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_RESPONSE);
  serialFieldSep();
  Serial.print((int)cmd_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialFieldSep();
  Serial.print((int)value2);
  serialLineEnd();
}

/**
 * @brief Sends a response with three payload fields.
 *
 * @param[in]  cmd_code Command code
 * @param[in]  value1 First payload value
 * @param[in]  value2 Second payload value
 * @param[in]  value3 Third payload value
 * @param[out] none
 * @return     void
 */
inline void sendResponseData3(uint16_t cmd_code,
                              uint16_t value1,
                              uint16_t value2,
                              uint16_t value3) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_RESPONSE);
  serialFieldSep();
  Serial.print((int)cmd_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialFieldSep();
  Serial.print((int)value2);
  serialFieldSep();
  Serial.print((int)value3);
  serialLineEnd();
}

/**
 * @brief Sends a response with four payload fields.
 *
 * @param[in]  cmd_code Command code
 * @param[in]  value1 First payload value
 * @param[in]  value2 Second payload value
 * @param[in]  value3 Third payload value
 * @param[in]  value4 Fourth payload value
 * @param[out] none
 * @return     void
 */
inline void sendResponseData4(uint16_t cmd_code,
                              uint16_t value1,
                              uint16_t value2,
                              uint16_t value3,
                              uint16_t value4) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_RESPONSE);
  serialFieldSep();
  Serial.print((int)cmd_code);
  serialFieldSep();
  Serial.print((int)value1);
  serialFieldSep();
  Serial.print((int)value2);
  serialFieldSep();
  Serial.print((int)value3);
  serialFieldSep();
  Serial.print((int)value4);
  serialLineEnd();
}

/**
 * @brief Sends a fault frame.
 *
 * @param[in]  fault_code Fault code
 * @param[out] none
 * @return     void
 */
inline void sendFault(uint8_t fault_code) {
  Serial.print((int)g_robot_id);
  serialFieldSep();
  Serial.print((int)MSG_FAULT);
  serialFieldSep();
  Serial.print((int)fault_code);
  serialLineEnd();
}

/**
 * @brief Sends an application sensor event.
 *
 * @param[in]  l Left binary sensor value
 * @param[in]  m Middle binary sensor value
 * @param[in]  r Right binary sensor value
 * @param[in]  tl Left raw sensor time
 * @param[in]  tm Middle raw sensor time
 * @param[in]  tr Right raw sensor time
 * @param[out] none
 * @return     void
 */
inline void sendSensorEvent(uint8_t l, uint8_t m, uint8_t r,
                            unsigned int tl, unsigned int tm, unsigned int tr) {
  sendEventData6(EV_APP_SENS, l, m, r, tl, tm, tr);
}

/**
 * @brief Sends a lap-completed event.
 *
 * @param[in]  lap Current lap count
 * @param[out] none
 * @return     void
 */
inline void sendLapEvent(uint16_t lap) {
  sendEventData1(EV_APP_LAP, lap);
}
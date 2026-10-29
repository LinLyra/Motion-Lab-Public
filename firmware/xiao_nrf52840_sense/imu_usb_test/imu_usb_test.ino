#include <Arduino.h>
#include <LSM6DS3.h>
#include <Wire.h>

namespace {

constexpr uint32_t kBaudRate = 115200;
constexpr uint32_t kSampleIntervalUs = 20000;  // 50 Hz
constexpr uint32_t kHeartbeatIntervalMs = 500;

LSM6DS3 imu(I2C_MODE, 0x6A);

uint32_t sequence_number = 0;
uint32_t next_sample_us = 0;
uint32_t next_heartbeat_ms = 0;
bool led_on = false;

void setLed(bool on) {
  // The XIAO nRF52840 Sense user LED is active-low.
  digitalWrite(LED_BUILTIN, on ? LOW : HIGH);
}

}  // namespace

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  setLed(false);

  Serial.begin(kBaudRate);
  const uint32_t serial_wait_started_ms = millis();
  while (!Serial && millis() - serial_wait_started_ms < 5000) {
    delay(10);
  }

  Wire.begin();
  if (imu.begin() != 0) {
    Serial.println("ERROR,LSM6DS3_NOT_FOUND");
    while (true) {
      setLed(true);
      delay(100);
      setLed(false);
      delay(100);
    }
  }

  Serial.println("LYKON_XIAO_IMU_V1");
  Serial.println("seq,timestamp_us,acc_x_g,acc_y_g,acc_z_g,gyro_x_dps,gyro_y_dps,gyro_z_dps");

  next_sample_us = micros();
  next_heartbeat_ms = millis();
}

void loop() {
  const uint32_t now_ms = millis();
  if (static_cast<int32_t>(now_ms - next_heartbeat_ms) >= 0) {
    led_on = !led_on;
    setLed(led_on);
    next_heartbeat_ms += kHeartbeatIntervalMs;
  }

  const uint32_t now_us = micros();
  if (static_cast<int32_t>(now_us - next_sample_us) < 0) {
    return;
  }
  next_sample_us += kSampleIntervalUs;

  const float acc_x = imu.readFloatAccelX();
  const float acc_y = imu.readFloatAccelY();
  const float acc_z = imu.readFloatAccelZ();
  const float gyro_x = imu.readFloatGyroX();
  const float gyro_y = imu.readFloatGyroY();
  const float gyro_z = imu.readFloatGyroZ();

  Serial.print(sequence_number++);
  Serial.print(',');
  Serial.print(now_us);
  Serial.print(',');
  Serial.print(acc_x, 6);
  Serial.print(',');
  Serial.print(acc_y, 6);
  Serial.print(',');
  Serial.print(acc_z, 6);
  Serial.print(',');
  Serial.print(gyro_x, 6);
  Serial.print(',');
  Serial.print(gyro_y, 6);
  Serial.print(',');
  Serial.println(gyro_z, 6);
}

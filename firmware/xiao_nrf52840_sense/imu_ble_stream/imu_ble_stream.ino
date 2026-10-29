#include <Arduino.h>
#include <ArduinoBLE.h>
#include <LSM6DS3.h>
#include <PDM.h>
#include <Wire.h>

#ifndef LYKON_DEVICE_NUMBER
#define LYKON_DEVICE_NUMBER 001
#endif

#define LYKON_STRINGIFY_INNER(value) #value
#define LYKON_STRINGIFY(value) LYKON_STRINGIFY_INNER(value)

namespace {

constexpr uint32_t kBaudRate = 115200;
constexpr uint32_t kSampleRateHz = 100;
constexpr uint32_t kSampleIntervalUs = 1000000UL / kSampleRateHz;
constexpr uint32_t kHeartbeatIntervalMs = 500;
constexpr uint32_t kMicrophoneSampleRateHz = 16000;
constexpr int kMicrophoneGain = 30;
constexpr char kDeviceName[] = "LYKON-" LYKON_STRINGIFY(LYKON_DEVICE_NUMBER);
constexpr char kSensorId[] = "IMU" LYKON_STRINGIFY(LYKON_DEVICE_NUMBER);
constexpr char kFirmwareVersion[] = "xiao-imu-mic-ble-v3";

// Custom LYKON service and characteristics.
constexpr char kServiceUuid[] = "5d7a0001-6f7e-4d8b-9a66-7c2e8b7f1000";
constexpr char kSampleUuid[] = "5d7a0002-6f7e-4d8b-9a66-7c2e8b7f1000";
constexpr char kInfoUuid[] = "5d7a0003-6f7e-4d8b-9a66-7c2e8b7f1000";
constexpr char kAudioLevelUuid[] = "5d7a0004-6f7e-4d8b-9a66-7c2e8b7f1000";

// One sample is 20 bytes. Two samples are batched per notification to reduce
// BLE notification overhead while preserving a 100 Hz sensor sample rate.
// All fields are little-endian. Acceleration is mg; gyro is 0.1 deg/s.
struct __attribute__((packed)) ImuPacketV1 {
  uint32_t seq;
  uint32_t t_node_us;
  int16_t ax_mg;
  int16_t ay_mg;
  int16_t az_mg;
  int16_t gx_ddeg_s;
  int16_t gy_ddeg_s;
  int16_t gz_ddeg_s;
};

static_assert(sizeof(ImuPacketV1) == 20, "BLE sample packet must be 20 bytes");

// Audio features are sent separately so existing IMU receivers stay compatible.
// RMS and peak use raw signed 16-bit PCM units.
struct __attribute__((packed)) AudioLevelPacketV1 {
  uint32_t seq;
  uint32_t t_node_us;
  uint16_t rms_pcm;
  uint16_t peak_pcm;
};

static_assert(sizeof(AudioLevelPacketV1) == 12, "BLE audio packet must be 12 bytes");

LSM6DS3 imu(I2C_MODE, 0x6A);
BLEService lykonService(kServiceUuid);
constexpr uint8_t kSamplesPerNotification = 2;
BLECharacteristic sampleCharacteristic(
    kSampleUuid, BLENotify, sizeof(ImuPacketV1) * kSamplesPerNotification, true);
BLEStringCharacteristic infoCharacteristic(kInfoUuid, BLERead, 128);
BLECharacteristic audioLevelCharacteristic(
    kAudioLevelUuid, BLENotify, sizeof(AudioLevelPacketV1), true);

uint32_t sequenceNumber = 0;
uint32_t nextSampleUs = 0;
uint32_t nextHeartbeatMs = 0;
bool ledOn = false;
ImuPacketV1 sampleBatch[kSamplesPerNotification];
uint8_t sampleBatchCount = 0;
int16_t pdmBuffer[256];
volatile uint32_t audioFrameSequence = 0;
volatile uint32_t audioFrameTimestampUs = 0;
volatile uint16_t audioFrameRms = 0;
volatile uint16_t audioFramePeak = 0;
volatile bool audioFrameReady = false;

void setLed(bool on) {
  digitalWrite(LED_BUILTIN, on ? LOW : HIGH);
}

int16_t clampToInt16(float value) {
  if (value > 32767.0f) return 32767;
  if (value < -32768.0f) return -32768;
  return static_cast<int16_t>(lroundf(value));
}

void fail(const char* message) {
  Serial.println(message);
  while (true) {
    setLed(true);
    delay(100);
    setLed(false);
    delay(100);
  }
}

void onPdmData() {
  const int bytesAvailable = PDM.available();
  if (bytesAvailable <= 0) return;

  const int bytesToRead = min(bytesAvailable, static_cast<int>(sizeof(pdmBuffer)));
  const int bytesRead = PDM.read(pdmBuffer, bytesToRead);
  const int sampleCount = bytesRead / static_cast<int>(sizeof(int16_t));
  if (sampleCount <= 0) return;

  uint64_t sumSquares = 0;
  uint16_t peak = 0;
  for (int i = 0; i < sampleCount; ++i) {
    const int32_t sample = pdmBuffer[i];
    const uint16_t magnitude = static_cast<uint16_t>(abs(sample));
    if (magnitude > peak) peak = magnitude;
    sumSquares += static_cast<uint64_t>(sample * sample);
  }

  audioFrameRms = static_cast<uint16_t>(
      sqrtf(static_cast<float>(sumSquares) / static_cast<float>(sampleCount)));
  audioFramePeak = peak;
  audioFrameTimestampUs = micros();
  ++audioFrameSequence;
  audioFrameReady = true;
}

}  // namespace

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  setLed(false);

  Serial.begin(kBaudRate);
  const uint32_t serialWaitStartedMs = millis();
  while (!Serial && millis() - serialWaitStartedMs < 3000) {
    delay(10);
  }

  Wire.begin();
  if (imu.begin() != 0) {
    fail("ERROR,LSM6DS3_NOT_FOUND");
  }

  PDM.onReceive(onPdmData);
  PDM.setBufferSize(sizeof(pdmBuffer));
  PDM.setGain(kMicrophoneGain);
  if (!PDM.begin(1, kMicrophoneSampleRateHz)) {
    fail("ERROR,PDM_MIC_NOT_FOUND");
  }

  if (!BLE.begin()) {
    fail("ERROR,BLE_INIT_FAILED");
  }

  BLE.setLocalName(kDeviceName);
  BLE.setDeviceName(kDeviceName);
  BLE.setAdvertisedService(lykonService);
  lykonService.addCharacteristic(sampleCharacteristic);
  lykonService.addCharacteristic(infoCharacteristic);
  lykonService.addCharacteristic(audioLevelCharacteristic);
  BLE.addService(lykonService);

  String info = String("protocol=1;sensor=") + kSensorId +
                ";imu=LSM6DS3TR-C;hz=" + kSampleRateHz +
                ";mic=PDM;mic_hz=" + kMicrophoneSampleRateHz +
                ";fw=" + kFirmwareVersion;
  infoCharacteristic.writeValue(info);
  BLE.advertise();

  Serial.println("LYKON_XIAO_IMU_MIC_BLE_V1");
  Serial.print("BLE_ADDRESS,");
  Serial.println(BLE.address());
  Serial.println("seq,t_node_us,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,mic_rms,mic_peak,ble_subscribed");

  nextSampleUs = micros();
  nextHeartbeatMs = millis();
}

void loop() {
  BLE.poll();

  if (audioFrameReady) {
    noInterrupts();
    const AudioLevelPacketV1 audioPacket{
        audioFrameSequence, audioFrameTimestampUs, audioFrameRms, audioFramePeak};
    audioFrameReady = false;
    interrupts();

    if (audioLevelCharacteristic.subscribed()) {
      audioLevelCharacteristic.writeValue(
          reinterpret_cast<const uint8_t*>(&audioPacket), sizeof(audioPacket));
    }
  }

  const uint32_t nowMs = millis();
  if (static_cast<int32_t>(nowMs - nextHeartbeatMs) >= 0) {
    ledOn = !ledOn;
    setLed(ledOn);
    nextHeartbeatMs += kHeartbeatIntervalMs;
  }

  const uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - nextSampleUs) < 0) {
    return;
  }
  nextSampleUs += kSampleIntervalUs;

  const float ax = imu.readFloatAccelX();
  const float ay = imu.readFloatAccelY();
  const float az = imu.readFloatAccelZ();
  const float gx = imu.readFloatGyroX();
  const float gy = imu.readFloatGyroY();
  const float gz = imu.readFloatGyroZ();

  ImuPacketV1 packet{
      sequenceNumber++, nowUs,
      clampToInt16(ax * 1000.0f), clampToInt16(ay * 1000.0f), clampToInt16(az * 1000.0f),
      clampToInt16(gx * 10.0f), clampToInt16(gy * 10.0f), clampToInt16(gz * 10.0f)};

  const bool subscribed = sampleCharacteristic.subscribed();
  if (subscribed) {
    sampleBatch[sampleBatchCount++] = packet;
    if (sampleBatchCount == kSamplesPerNotification) {
      sampleCharacteristic.writeValue(reinterpret_cast<const uint8_t*>(sampleBatch), sizeof(sampleBatch));
      sampleBatchCount = 0;
    }
  } else {
    sampleBatchCount = 0;
  }

  if (Serial) {
    Serial.print(packet.seq);
    Serial.print(',');
    Serial.print(packet.t_node_us);
    Serial.print(',');
    Serial.print(ax, 6);
    Serial.print(',');
    Serial.print(ay, 6);
    Serial.print(',');
    Serial.print(az, 6);
    Serial.print(',');
    Serial.print(gx, 6);
    Serial.print(',');
    Serial.print(gy, 6);
    Serial.print(',');
    Serial.print(gz, 6);
    Serial.print(',');
    Serial.print(audioFrameRms);
    Serial.print(',');
    Serial.print(audioFramePeak);
    Serial.print(',');
    Serial.println(subscribed ? 1 : 0);
  }
}

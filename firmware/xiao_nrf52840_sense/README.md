# XIAO nRF52840 Sense firmware

## USB IMU test

`imu_usb_test/imu_usb_test.ino` verifies the onboard LSM6DS3TR-C and streams
accelerometer and gyroscope samples as CSV over USB serial at 50 Hz.

## BLE IMU stream

`imu_ble_stream/imu_ble_stream.ino` is the combined collection firmware:

- samples the onboard six-axis IMU at 100 Hz;
- samples the onboard PDM microphone at 16 kHz;
- publishes microphone RMS and peak levels through BLE characteristic
  `5d7a0004-6f7e-4d8b-9a66-7c2e8b7f1000` as `<IIHH>`;
- preserves `seq` and the device-local `t_node_us`;
- batches two 20-byte samples per BLE notification (`<IIhhhhhh`, little-endian)
  to retain 100 Hz sampling with lower notification overhead;
- keeps USB CSV output for debugging;
- the device number is selected at compile time; the default is
  `LYKON-001` / `IMU001`.

The IMU payload stores acceleration in mg and angular velocity in 0.1 deg/s.
The Mac logger converts them back to g and deg/s and adds experiment metadata
and `host_received_us`. The microphone characteristic contains acoustic
features rather than raw audio so it can run beside the 100 Hz IMU stream.
Fields unavailable on this six-axis board (magnetometer, quaternion, battery)
are intentionally left blank rather than fabricated.

Compile:

```bash
arduino-cli compile \
  --fqbn Seeeduino:mbed:xiaonRF52840Sense \
  firmware/xiao_nrf52840_sense/imu_ble_stream
```

Compile a numbered unit (for example unit 002):

```bash
arduino-cli compile \
  --fqbn Seeeduino:mbed:xiaonRF52840Sense \
  --build-property 'compiler.cpp.extra_flags=-DLYKON_DEVICE_NUMBER=002' \
  firmware/xiao_nrf52840_sense/imu_ble_stream
```

After uploading, install the Mac receiver dependency and record a session:

```bash
python3 -m pip install bleak
python3 tools/ble_imu_logger.py \
  --device-name LYKON-001 \
  --session S001 --player P01 --sensor IMU001 --side right \
  --output data/S001_IMU001.csv
```

Compile:

```bash
arduino-cli compile \
  --fqbn Seeeduino:mbed:xiaonRF52840Sense \
  firmware/xiao_nrf52840_sense/imu_usb_test
```

Upload (replace the port if it changes):

```bash
arduino-cli upload \
  --fqbn Seeeduino:mbed:xiaonRF52840Sense \
  --port /dev/cu.usbmodem101 \
  firmware/xiao_nrf52840_sense/imu_usb_test
```

Monitor:

```bash
arduino-cli monitor \
  --port /dev/cu.usbmodem101 \
  --config baudrate=115200
```

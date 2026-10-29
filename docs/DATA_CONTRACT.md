# Data contract

## Timing model

Every wearable IMU and acoustic feature packet contains a monotonically
increasing sequence number and a device-clock timestamp. The collector adds a
host receive timestamp and derives a session-local aligned timestamp while
retaining the original clock. UWB records retain their block/sequence values and
host receive timestamp. Host timestamps provide an initial alignment layer; a
formal synchronisation protocol is still required for high-accuracy fusion.

## Core identifiers

- `session_id`: pseudonymous capture session
- `participant_code`: non-identifying research code, for example `P001`
- `sensor_id`: logical wearable identifier
- `uwb_tag_id`: logical tag identifier
- `anchor_id`: logical anchor identifier
- `schema_version`: versioned data-contract identifier
- `firmware_version`: firmware provenance

## IMU fields

The canonical SI representation uses acceleration in `m/s²`, angular velocity
in `rad/s`, and timestamps in microseconds. Collector-native CSV may retain `g`
and `deg/s`; conversion must be explicit and recorded in processing provenance.

## UWB fields

UWB rows contain tag, anchor, sequence, status, range and receive time. Failed
or timed-out measurements remain present with a status and missing range rather
than being silently dropped.

## Immutability and provenance

Raw capture files are append-only during acquisition and immutable afterwards.
Cleaning, interpolation, alignment and feature extraction produce separate
derived files. Every derived dataset records its source assets, configuration,
software version and quality flags.


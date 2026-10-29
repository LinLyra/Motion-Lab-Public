"""Versioned contracts for wearable sensor files.

Raw capture files deliberately do not contain labels.  Labels live in the
separate action/event label tables described in ``docs/data_schema_v2.md``.
The legacy contract remains readable so historical experiments do not break.
"""

SENSOR_RAW_V2_REQUIRED_COLUMNS = [
    "session_id",
    "player_id",
    "sensor_id",
    "side",
    "seq",
    "t_node_us",
    "host_received_us",
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
]

SENSOR_RAW_V2_TIMESTAMP_PRIORITY = [
    "synced_timestamp_us",
    "t_node_us",
    "host_received_us",
]

LEGACY_REQUIRED_COLUMNS = [
    "session_id",
    "player_id",
    "sensor_id",
    "side",
    "seq",
    "timestamp_us",
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
]

# Backwards-compatible import name.  New code should use the versioned names.
REQUIRED_COLUMNS = SENSOR_RAW_V2_REQUIRED_COLUMNS

OPTIONAL_COLUMNS = [
    "sync_rtt_us",
    "mx", "my", "mz",
    "qw", "qx", "qy", "qz", "roll", "pitch", "yaw",
    "linear_acc_x", "linear_acc_y", "linear_acc_z",
    "gravity_x", "gravity_y", "gravity_z",
    "calibration_status", "battery", "rssi", "sampling_rate",
    "firmware_version",
]

LABELS_V1 = ["idle", "dribble", "pass", "shot", "jump", "sprint"]

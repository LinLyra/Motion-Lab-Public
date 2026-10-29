import tempfile
import unittest
from pathlib import Path

import pandas as pd

from lykon_motion.data.loaders import (
    SensorDataContractError,
    detect_sensor_raw_version,
    load_standard_csv,
)


class SensorDataContractTests(unittest.TestCase):
    def test_v2_raw_file_does_not_require_label_or_magnetometer(self):
        row = {
            "session_id": "session-1",
            "player_id": "player-1",
            "sensor_id": "left-arm-1",
            "side": "left",
            "seq": 1,
            "t_node_us": 100,
            "host_received_us": 130,
            "synced_timestamp_us": 110,
            "ax": 0.1,
            "ay": 0.2,
            "az": 9.8,
            "gx": 1.0,
            "gy": 2.0,
            "gz": 3.0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sensor_raw.csv"
            pd.DataFrame([row]).to_csv(path, index=False)
            loaded = load_standard_csv(path)

        self.assertEqual(loaded.attrs["sensor_contract_version"], "sensor_raw.v2")
        self.assertEqual(loaded.loc[0, "timestamp_us"], 110)
        self.assertNotIn("label", loaded.columns)

    def test_v2_timestamp_falls_back_to_node_clock(self):
        columns = {
            "session_id": ["session-1"],
            "player_id": ["player-1"],
            "sensor_id": ["right-arm-1"],
            "side": ["right"],
            "seq": [2],
            "t_node_us": [200],
            "host_received_us": [240],
            "synced_timestamp_us": [None],
            "ax": [0.1],
            "ay": [0.2],
            "az": [9.8],
            "gx": [1.0],
            "gy": [2.0],
            "gz": [3.0],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sensor_raw.csv"
            pd.DataFrame(columns).to_csv(path, index=False)
            loaded = load_standard_csv(path)

        self.assertEqual(loaded.loc[0, "timestamp_us"], 200)

    def test_unknown_contract_reports_both_missing_sets(self):
        with self.assertRaises(SensorDataContractError):
            detect_sensor_raw_version(["ax", "ay", "az"])


if __name__ == "__main__":
    unittest.main()

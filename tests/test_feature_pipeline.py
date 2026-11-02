import unittest

import numpy as np
import pandas as pd

from lykon_motion.data.preprocess import filter_imu
from lykon_motion.features.extract import extract_window_features
from lykon_motion.features.windowing import make_windows


class FeaturePipelineTests(unittest.TestCase):
    def test_filter_window_and_feature_path(self):
        sampling_rate = 50
        sample_count = 150
        time_s = np.arange(sample_count) / sampling_rate
        frame = pd.DataFrame(
            {
                "session_id": "synthetic-session",
                "player_id": "P001",
                "side": "right",
                "timestamp_us": (time_s * 1_000_000).astype(int),
                "label": "shot",
                "ax": np.sin(2 * np.pi * 2 * time_s),
                "ay": np.cos(2 * np.pi * 2 * time_s),
                "az": np.full(sample_count, 9.81),
                "gx": np.sin(2 * np.pi * 3 * time_s),
                "gy": np.zeros(sample_count),
                "gz": np.zeros(sample_count),
            }
        )
        channels = ["ax", "ay", "az", "gx", "gy", "gz"]

        filtered = filter_imu(frame, fs=sampling_rate)
        windows, metadata = make_windows(
            filtered,
            sampling_rate_hz=sampling_rate,
            window_seconds=2.0,
            step_seconds=1.0,
            channels=channels,
        )
        features = extract_window_features(
            windows, metadata, channels, fs=sampling_rate
        )

        self.assertEqual(windows.shape, (2, len(channels), 100))
        self.assertEqual(features["label"].tolist(), ["shot", "shot"])
        self.assertTrue(np.isfinite(features["acc_norm_mean"]).all())
        self.assertAlmostEqual(features.loc[0, "ax_dom_freq"], 2.0, places=6)


if __name__ == "__main__":
    unittest.main()

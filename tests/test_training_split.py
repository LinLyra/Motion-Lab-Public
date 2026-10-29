import unittest
import tempfile
from pathlib import Path

import pandas as pd

from lykon_motion.models.train_sklearn import choose_split_groups, train_random_forest


class TrainingSplitTests(unittest.TestCase):
    def test_player_boundary_has_priority(self):
        frame = pd.DataFrame({
            "player_id": ["P001", "P001", "P002", "P002"],
            "session_id": ["a", "b", "c", "d"],
        })
        groups, column = choose_split_groups(frame)
        self.assertEqual(column, "player_id")
        self.assertEqual(groups.tolist(), ["P001", "P001", "P002", "P002"])

    def test_random_window_fallback_is_forbidden(self):
        frame = pd.DataFrame({"player_id": ["P001", "P001"]})
        with self.assertRaisesRegex(ValueError, "random window splitting is disabled"):
            choose_split_groups(frame)

    def test_synthetic_data_requires_explicit_opt_in(self):
        frame = pd.DataFrame({
            "player_id": ["P01", "P02"],
            "session_id": ["dummy_session", "dummy_session"],
            "label": ["idle", "shot"],
            "feature": [0.0, 1.0],
        })
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "features.csv"
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Synthetic/dummy"):
                train_random_forest(path, root / "output")


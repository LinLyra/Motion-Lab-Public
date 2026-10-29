from __future__ import annotations
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder


def choose_split_groups(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """Choose the strongest available boundary for leakage-safe evaluation."""
    for column in ("player_id", "subject", "session_id", "source_file"):
        if column in df.columns and df[column].nunique(dropna=True) >= 2:
            return df[column].astype(str), column
    raise ValueError(
        "Leakage-safe evaluation requires at least two players, subjects, "
        "sessions, or source files; random window splitting is disabled."
    )


def train_random_forest(
    features_csv: str | Path,
    out_dir: str | Path,
    *,
    allow_synthetic: bool = False,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(features_csv)
    synthetic_mask = pd.Series(False, index=df.index)
    if "session_id" in df.columns:
        synthetic_mask |= df["session_id"].astype(str).str.contains(
            "dummy|synthetic", case=False, regex=True
        )
    if synthetic_mask.any() and not allow_synthetic:
        raise ValueError(
            "Synthetic/dummy features detected. Pass allow_synthetic=True only "
            "for a demo run; this output is not a scientific result."
        )
    y = df["label"]
    groups, group_column = choose_split_groups(df)
    drop_cols = [
        "session_id", "player_id", "subject", "source_file", "side",
        "start_timestamp_us", "end_timestamp_us", "label",
    ]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    X = X.select_dtypes(include=["number"]).fillna(0)

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    splitter = GroupShuffleSplit(test_size=0.25, n_splits=1, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y_enc, groups=groups))
    if set(groups.iloc[train_idx]) & set(groups.iloc[test_idx]):
        raise RuntimeError("Group leakage detected between train and test")
    clf = RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")
    clf.fit(X.iloc[train_idx], y_enc[train_idx])
    pred = clf.predict(X.iloc[test_idx])
    labels = list(range(len(le.classes_)))
    report = classification_report(
        y_enc[test_idx], pred, labels=labels, target_names=le.classes_, zero_division=0
    )
    cm = confusion_matrix(y_enc[test_idx], pred, labels=labels)

    joblib.dump({
        "model": clf,
        "label_encoder": le,
        "features": list(X.columns),
        "split_group_column": group_column,
        "train_groups": sorted(set(groups.iloc[train_idx])),
        "test_groups": sorted(set(groups.iloc[test_idx])),
        "contains_synthetic_data": bool(synthetic_mask.any()),
    }, out_dir / "rf_model.joblib")
    (out_dir / "rf_report.txt").write_text(report, encoding="utf-8")
    pd.DataFrame(cm, index=le.classes_, columns=le.classes_).to_csv(out_dir / "rf_confusion_matrix.csv")
    return {
        "report": report,
        "model_path": str(out_dir / "rf_model.joblib"),
        "split_group_column": group_column,
    }

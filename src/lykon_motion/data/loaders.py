from pathlib import Path
import pandas as pd
from .schema import (
    LEGACY_REQUIRED_COLUMNS,
    SENSOR_RAW_V2_REQUIRED_COLUMNS,
    SENSOR_RAW_V2_TIMESTAMP_PRIORITY,
)


class SensorDataContractError(ValueError):
    """Raised when a sensor file matches neither supported raw-data contract."""


def detect_sensor_raw_version(columns) -> str:
    column_set = set(columns)
    if set(SENSOR_RAW_V2_REQUIRED_COLUMNS).issubset(column_set):
        return "sensor_raw.v2"
    if set(LEGACY_REQUIRED_COLUMNS).issubset(column_set):
        return "sensor_raw.legacy"

    v2_missing = sorted(set(SENSOR_RAW_V2_REQUIRED_COLUMNS) - column_set)
    legacy_missing = sorted(set(LEGACY_REQUIRED_COLUMNS) - column_set)
    raise SensorDataContractError(
        "Sensor file does not match a supported contract. "
        f"sensor_raw.v2 missing={v2_missing}; legacy missing={legacy_missing}"
    )


def _canonical_timestamp(df: pd.DataFrame, version: str) -> pd.Series:
    if version == "sensor_raw.legacy":
        return df["timestamp_us"]

    for column in SENSOR_RAW_V2_TIMESTAMP_PRIORITY:
        if column in df.columns and df[column].notna().any():
            # A synchronized clock may be unavailable for early captures.  Fill
            # only its gaps with the node clock, then the host receive clock.
            result = df[column].copy()
            for fallback in SENSOR_RAW_V2_TIMESTAMP_PRIORITY:
                if fallback in df.columns:
                    result = result.fillna(df[fallback])
            return result
    raise SensorDataContractError("sensor_raw.v2 has no usable timestamp values")


def load_standard_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path)
    version = detect_sensor_raw_version(df.columns)
    df["timestamp_us"] = _canonical_timestamp(df, version)
    if df["timestamp_us"].isna().any():
        raise SensorDataContractError(f"{path.name} contains rows without a usable timestamp")
    df.attrs["sensor_contract_version"] = version
    df = df.sort_values(["session_id", "player_id", "side", "timestamp_us"]).reset_index(drop=True)
    df.attrs["sensor_contract_version"] = version
    return df


def load_folder(folder: str | Path) -> pd.DataFrame:
    folder = Path(folder)
    files = sorted(folder.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {folder}")
    return pd.concat([load_standard_csv(f) for f in files], ignore_index=True)

# LYKON Research Console

Local-only Research Console for four-device BLE capture, one DWM3001CDK UWB
tag with three anchors, and recorded-data replay. It does not upload or delete
any data.

Run:

```bash
python3 research_console/server.py
```

Then open <http://127.0.0.1:8765>. The live mode automatically searches for
`LYKON-001` through `LYKON-004`, maintains separate buffers and quality counters,
and writes local CSV files under `data/local_capture/<session>/` when recording.
The console reads the UWB tag USB serial from the ignored local registry
`configs/device_registry.local.json`, starts one-to-many ranging against
addresses `0x0001` through `0x0003`, displays each range, and writes `UWB.csv`
into the same session folder. Copy `configs/device_registry.example.json` when
setting up a new machine. Historical replay remains available for a local
capture file when present.

Each XIAO microphone streams non-reconstructable RMS and peak PCM level
features through the audio BLE characteristic. The live console displays those
features and records `AUDIO_IMU001.csv` through `AUDIO_IMU004.csv`. Raw audio is
not transmitted or stored.

# Algorithm and data-processing pipeline

This document maps each research-processing capability to executable code. It
separates implemented engineering from validation that still requires a larger,
ground-truthed field dataset.

## End-to-end flow

```text
BLE IMU packets and UWB ranges
        |
        v
immutable device, node-clock and host-receive timestamps
        |
        v
schema validation and canonical timestamp selection
        |
        v
low-pass filtering and vector-magnitude construction
        |
        v
overlapping temporal windows
        |
        v
time-domain, peak and frequency-domain features
        |
        +---------------------+
        |                     |
        v                     v
interpretable rules     classical ML baseline
                              |
                              v
             participant/session-grouped evaluation
```

## Implemented capabilities

| Stage | Method | Primary implementation | Research purpose |
| --- | --- | --- | --- |
| Ingestion | Versioned CSV contract validation | `src/lykon_motion/data/loaders.py` | Reject malformed files before analysis |
| Time base | Synchronized, node and host timestamp priority | `src/lykon_motion/data/loaders.py` | Preserve usable timing while exposing fallback behaviour |
| Filtering | Third-order Butterworth low-pass filter | `src/lykon_motion/data/preprocess.py` | Reduce high-frequency sensor noise |
| Derived signals | Acceleration, gyroscope and magnetometer norms | `src/lykon_motion/data/preprocess.py` | Produce orientation-robust motion intensity signals |
| Segmentation | Fixed-length overlapping windows with majority labels | `src/lykon_motion/features/windowing.py` | Convert continuous streams into modelling samples |
| Features | Mean, standard deviation, extrema, peak-to-peak range, peak count and dominant frequency | `src/lykon_motion/features/extract.py` | Capture intensity, variability, rhythm and impact structure |
| Interpretable baseline | Threshold rules for idle, dribble, pass, shot, jump and sprint | `src/lykon_motion/rules/basketball_rules.py` | Provide inspectable hypotheses before learned models |
| Classical ML baseline | Class-balanced 300-tree Random Forest | `src/lykon_motion/models/train_sklearn.py` | Establish a reproducible non-temporal benchmark |
| Evaluation safety | GroupShuffleSplit by participant, subject, session or source file | `src/lykon_motion/models/train_sklearn.py` | Prevent overlapping windows from leaking across train and test sets |
| Evaluation outputs | Classification report and confusion matrix | `src/lykon_motion/models/train_sklearn.py` | Report per-class errors rather than accuracy alone |
| Bilateral/video research | Cross-correlation lag, dominant frequency, MediaPipe world pose and motion templates | `scripts/24_build_shot_features.py`, `scripts/32_extract_world_pose.py`, `scripts/33_build_motion_template.py` | Study coordination and support external ground truth |

## Reproducible demonstration

The public repository contains synthetic data only. It can exercise the
pipeline without exposing participant data:

```bash
python scripts/01_generate_dummy_data.py
python scripts/02_build_features.py
python scripts/03_train_baseline.py --allow-synthetic
python scripts/04_run_rules.py
```

Synthetic outputs demonstrate execution and software interfaces. They must not
be interpreted as evidence of real-world recognition performance.

## Evaluation design

Random splitting of overlapping windows is deliberately disabled. Evaluation
must use the strongest available independent grouping boundary, preferably a
held-out participant and otherwise a held-out session or source recording. The
saved model artifact records the selected grouping field and the train/test
groups so that leakage can be audited.

The intended field-study reporting includes:

- per-class precision, recall and F1;
- confusion matrices;
- participant-independent results;
- BLE loss, reconnection and effective sample-rate distributions;
- timing offset, jitter and drift;
- UWB range error under line-of-sight and occlusion;
- failure cases and calibration sensitivity.

## Current limitations and next methods

The implemented rules are hypotheses requiring calibration. The Random Forest
is a classical baseline, not the final model. Current development priorities
are ground-truth event annotation, direct adapters from the 100 Hz live-capture
schema into modelling windows, surveyed-anchor UWB localisation, multimodal
alignment and comparison with temporal models. No accuracy or localisation
claim should be made until those stages are evaluated on held-out participants.

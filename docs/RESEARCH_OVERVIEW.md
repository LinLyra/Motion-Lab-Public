# Research overview

## Research question

How reliably can a compact, low-cost wearable system combine inertial sensing
and UWB ranging to recognise basketball actions and estimate player movement in
real playing conditions?

## System architecture

```text
Four wearable nodes                 Court ranging network
LSM6DS3TR-C + PDM microphone        DWM3001CDK tag + three anchors
          |                                      |
100 Hz IMU + acoustic features             DS-TWR ranges
          | BLE                                  | USB
          +------------------+-------------------+
                             |
                 Local acquisition service
                             |
          immutable CSV streams + host timestamps
                             |
       validation -> alignment -> features -> models
                             |
          participant-independent evaluation
```

## Experimental priorities

1. Quantify BLE packet loss and reconnection behaviour during court movement.
2. Characterise UWB range error under line-of-sight, body occlusion and NLOS.
3. Measure timestamp offset, jitter and drift across wearable and UWB streams.
4. Establish video- or manually-verified action intervals as ground truth.
5. Compare rules, classical baselines and temporal models using participant-level
   splits rather than random window splits.
6. Report uncertainty, failure cases and calibration sensitivity alongside
   aggregate accuracy.

## Acoustic feature policy

The wearable samples its PDM microphone at 16 kHz but computes RMS and peak
amplitude on-device. Only those level features are transmitted. Raw waveform
audio is neither transmitted nor stored. These features may support impact,
ball-bounce or whistle candidate detection, but must not be represented as
semantic audio recognition without separate validation.

## Localisation scope

Each ranging result is a tag-to-anchor distance. Two-dimensional position
requires surveyed anchor coordinates, at least three usable ranges, geometric
solving, outlier handling and evaluation against ground truth. The current
console displays and stores ranges; it does not claim validated position error.


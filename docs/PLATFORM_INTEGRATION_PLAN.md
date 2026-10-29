# Motion Lab to Platform integration plan

## Ownership boundary

`lykon-platform` owns identity, consent, device registration, session state,
authorisation, uploads, job orchestration, and the research-console UI.

`lykon-motion-lab-v2` owns file-contract validation, clock synchronisation, data
quality, feature extraction, event detection, and reproducible research artifacts.

Raw high-frequency samples and video belong in object storage. PostgreSQL stores
metadata, status, provenance, labels, and references to artifacts—not every IMU row.

## First vertical slice: recorded data replay

1. Platform creates a session with stable player and device bindings.
2. Collector creates a versioned session manifest and immutable source files.
3. Platform issues signed uploads for left IMU, right IMU, optional UWB, and video.
4. Upload completion verifies byte length and SHA-256 checksum.
5. Worker invokes Motion Lab with asset references and a pipeline version.
6. Motion Lab produces a quality report and decimated waveform artifact.
7. Operations Web loads video plus waveform tiles on one session time axis.
8. A researcher creates manual labels without modifying source files.
9. Labels and quality decisions record author, timestamp, and revision.

## Required platform contracts

Suggested versioned endpoints or equivalent application-service methods:

```text
POST   /v1/research/sessions
POST   /v1/research/sessions/{id}/assets
POST   /v1/research/assets/{id}/complete
GET    /v1/research/sessions/{id}
GET    /v1/research/sessions/{id}/timeline
GET    /v1/research/sessions/{id}/quality
GET    /v1/research/sessions/{id}/waveforms?channel=&start_us=&end_us=&pixels=
GET    /v1/research/sessions/{id}/labels
POST   /v1/research/sessions/{id}/labels
PATCH  /v1/research/labels/{id}
POST   /v1/research/sessions/{id}/exports
```

Waveform responses should be downsampled for the requested viewport. The browser
must not download a complete multi-hour raw IMU file merely to draw a chart.

## Artifact contract

Each processing run writes a manifest similar to:

```json
{
  "contract_version": "lykon.processing-result.v1",
  "session_id": "...",
  "pipeline": {"name": "motion-lab", "version": "..."},
  "source_assets": [{"asset_id": "...", "sha256": "..."}],
  "artifacts": {
    "quality_report": "...",
    "waveform_pyramid": "...",
    "synchronisation_report": "..."
  },
  "quality_flags": [],
  "warnings": [],
  "generated_at": "UTC timestamp"
}
```

Do not store credentials or signed URLs in artifacts. Store stable object keys; the
Platform API creates short-lived URLs after authorisation.

## Live capture later

The edge collector uses the same session manifest and raw contracts. During capture
it may additionally send a low-rate preview stream over WebSocket. The authoritative
record remains the immutable uploaded file, so a browser disconnect cannot corrupt
the research session.

## Acceptance criteria

- The same input files and pipeline version reproduce the same quality artifacts.
- Every displayed number identifies its source asset and calculation version.
- Missing, partial, uncalibrated, and saturated data are visible states.
- Manual labels never alter raw files or machine predictions.
- Demo fixtures cannot be selected as research evidence.
- A user without the research role cannot download participant video or raw signals.

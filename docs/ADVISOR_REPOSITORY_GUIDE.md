# Advisor-facing repository guide

This repository documents a wearable basketball sensing system combining
four BLE IMU nodes, UWB ranging, optional video-derived supervision, and a
local research console.

## What an advisor release contains

- research questions, architecture, schemas, and synchronization assumptions;
- reproducible preprocessing, feature extraction, baseline modelling, and tests;
- XIAO nRF52840 Sense firmware and local acquisition tools;
- a synthetic session demonstrating the data contract;
- no participant recordings, raw video, real labels, or device serial numbers.

## What remains in controlled storage

- raw and derived IMU/UWB/video data;
- participant identity mapping and consent records;
- precise collection dates, locations, and hardware identifiers;
- private experiment notes and quality reports tied to a real session.

Use pseudonymous participant codes such as `P001` in the controlled dataset.
Keep the identity key encrypted and physically/logically separate from sensor
files. The Git repository should contain schemas and synthetic examples only.

## Recommended delivery

1. Create a new private GitHub repository from the generated advisor release.
   Do not reuse the current repository history.
2. Add the prospective advisor as a read-only collaborator where possible.
3. Share real research data separately through institution-approved storage.
4. Run `python3 tools/audit_advisor_release.py advisor_release` before every
   push or archive transfer.

The existing repository history contains legacy participant-name references and
derived artifacts. Removing files in a later commit does not remove them from
Git history, which is why the advisor release must start with fresh history.


# Research data security and handling

## Classification

| Class | Examples | Git policy |
| --- | --- | --- |
| Public | source code intended for release, empty schemas, public documentation | allowed after review |
| Internal | architecture, non-sensitive test fixtures, synthetic demo data | private repositories only |
| Confidential research | raw IMU/UWB captures, videos, labels, participant identifiers | never commit to Git |
| Secret | API keys, service-role credentials, signing keys, production `.env` files | secret manager only |

## Required controls

- Use anonymous research participant IDs; do not use names in capture filenames.
- Store consent records and identifying information separately from sensor files.
- Keep raw captures immutable and checksum every uploaded source asset.
- Record who created labels or corrections and when.
- Store server timestamps in UTC and preserve original device clocks separately.
- Use short-lived signed URLs for video and sensor downloads.
- Restrict research downloads to explicitly authorised roles.
- Define retention and deletion rules before collecting external participant data.
- Back up metadata and raw assets separately and test restoration.

## Local development

- `.env*`, private keys, databases, generated outputs, raw captures, participant
  videos, large model/data binaries, and local legacy repositories are ignored.
- `.env.example` may contain variable names only, never usable credentials.
- Before the first organisational push, run secret scanning across the complete Git
  history, not only the working tree.

## Session provenance

Every session bundle should include a manifest with:

- schema version and session ID;
- anonymous participant IDs and device IDs;
- hardware and firmware versions;
- capture start/end times and time zone;
- sampling configuration and clock metadata;
- source filenames, byte sizes, and SHA-256 checksums;
- consent/research protocol reference, without personal details;
- collector software version.

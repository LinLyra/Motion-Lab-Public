# Security policy

LYKON research captures may include sensitive participant video and biometric-like
movement data. Do not report vulnerabilities through a public issue containing
participant data, credentials, internal URLs, or raw captures.

Until a company security mailbox and private reporting channel are established,
repository owners should handle reports privately and record only a redacted issue
for remediation tracking.

Never commit:

- API keys, service-role credentials, certificates, or production `.env` files;
- raw IMU/UWB captures, participant video, consent records, or identifying metadata;
- production database dumps or signed asset URLs.

Rotate a secret immediately if it enters Git history. Deleting the working-tree file
is not sufficient; audit the history and revoke the credential before rewriting or
releasing the repository.

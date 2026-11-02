# Security policy

LYKON research captures may include sensitive participant video and biometric-like
movement data. Do not report vulnerabilities through a public issue containing
participant data, credentials, internal URLs, or raw captures.

Security concerns should be sent privately to the repository owner. Public issues
should contain only a redacted description and no research data.

Never commit:

- API keys, passwords, certificates, or usable `.env` files;
- raw IMU/UWB captures, participant video, consent records, or identifying metadata;
- database dumps or signed asset URLs.

Rotate a secret immediately if it enters Git history. Deleting the working-tree file
is not sufficient; audit the history and revoke the credential before rewriting or
releasing the repository.

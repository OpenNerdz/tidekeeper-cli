# Security Policy

## Supported Versions

Security fixes are made on the `main` branch and included in the next tagged
release. Users should update to the latest release before reporting issues.

## Reporting a Vulnerability

Please do not open a public issue for security-sensitive problems.

Report vulnerabilities through GitHub's private vulnerability reporting for this
repository, or contact the maintainers privately if that is unavailable. Include:

- The affected version or commit.
- The platform and install method.
- Steps to reproduce.
- The impact and any known workaround.

Redact access tokens, refresh tokens, cookies, account IDs, and personal data
from logs before sharing them.

## Token Handling

Tidekeeper stores TIDAL access and refresh tokens locally so it can reuse a
login session. Token files are written with owner-only permissions where the
platform supports POSIX file modes. Treat token files as secrets and avoid
including them in bug reports, screenshots, backups, or shell history.

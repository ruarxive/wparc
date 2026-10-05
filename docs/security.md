# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | ✅ Active          |
| < 1.0   | ❌ End-of-life     |

## Reporting a Vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Email the maintainer at **<ivan@begtin.tech>** with:

- a short description of the issue,
- reproduction steps (preferably a minimal command),
- impact (data leak, RCE, etc.).

You will receive an acknowledgement within **5 business days**. We aim
to ship a fix or mitigation within **30 days**, and to coordinate a
public disclosure once the fix is available.

## Security Posture

wparc is an HTTP client that **only** fetches publicly accessible data
from WordPress sites; it never opens a network socket inbound, never
handles credentials in cleartext, and never executes remote code.

The following practices are enforced in CI and `pyproject.toml`:

- `yaml.safe_load` (no arbitrary code execution from route files).
- `subprocess.run([...])` with argument lists (no shell injection).
- SSL verification enabled by default; opt-out via `--no-verify-ssl`.
- HTTPS by default; opt-out via `--no-https`.
- Domain validation rejects invalid hostnames before any HTTP call.
- File operations use `with open(...)` and explicit encoding.
- Cleanup of partial downloads on error.

## Known Limitations

- `--no-verify-ssl` disables certificate checks; this is **not safe** on
  untrusted networks.
- HTTP Basic Auth credentials passed via `--user/--password` are visible
  in the process listing; prefer environment variables in production.
- The `known_routes.yml` database is loaded at runtime; an attacker
  with write access to the package install directory could inject
  malicious routes. Mitigate by installing from a trusted source.
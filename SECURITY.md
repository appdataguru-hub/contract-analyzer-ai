# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | ✅ Yes             |

## Reporting a Vulnerability

We take the security of Contract Analyzer AI seriously. If you discover a security vulnerability, please follow these steps:

1. **Do not** disclose the vulnerability publicly (no GitHub Issues, no public discussions).
2. Send a description of the vulnerability to the project maintainers via email or private channel.
3. Include steps to reproduce, affected versions, and any potential impact.

You should receive a response within 48 hours. If the issue is confirmed, we will:

- Release a patch as soon as possible
- Acknowledge your contribution (if desired)
- Publicly disclose the issue after the fix is released

## Security Measures

This project implements the following security measures:

- ✅ **Input validation** — Pydantic schemas + file size limits
- ✅ **CORS whitelist** — configurable via environment
- ✅ **Optional API key authentication** — Bearer token
- ✅ **Error sanitization** — no stack trace leakage
- ✅ **Streaming file upload** — OOM protection
- ✅ **Thread-safe singletons** — race condition prevention

## Known Security Considerations

- Rate limiting is not implemented — consider adding nginx or slowapi for production deployments
- API keys and credentials are stored in environment variables — consider using Vault/KMS for production
- No audit logging — consider adding request/response logging for compliance

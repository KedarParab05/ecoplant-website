# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest (main) | ✅ |
| Older commits | ❌ |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Report security vulnerabilities by emailing: **security@ecoplant-pro.vercel.app**

Or use [GitHub Private Security Advisories](https://github.com/KedarParab05/ecoplant-website/security/advisories/new).

### What to include

- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

| Stage | Timeline |
|-------|----------|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix deployed | Within 30 days (critical: 7 days) |

### Scope

**In scope:**
- SQL / NoSQL injection
- XSS / CSRF
- Authentication bypass
- Privilege escalation
- Sensitive data exposure
- Supply chain attacks

**Out of scope:**
- Rate limiting bypass via distributed IPs
- Self-XSS
- Social engineering
- Physical access

### Safe Harbour

We will not take legal action against researchers who:
- Report in good faith
- Do not access or modify user data
- Do not degrade service availability
- Disclose privately before public disclosure

## Security Measures

This repository implements:
- Python-Jose JWT with algorithm pinning (`HS256` only, `none` blocked)
- bcrypt-12 password hashing
- Brute-force lockout (10 fails → 30 min ban)
- NoSQL injection blocking middleware
- XSS blocking middleware
- CSP, HSTS, X-Frame-Options, Permissions-Policy headers
- Rate limiting on all AI and auth endpoints
- Input validation via Pydantic + custom validators
- Magic-byte MIME verification on file uploads
- Constant-time comparisons to prevent timing attacks

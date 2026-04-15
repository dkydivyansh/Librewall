# Security Policy

## Overview

The Librewall team takes the security of this project seriously. We appreciate the efforts of security researchers and the broader community in helping us maintain a safe and reliable product. This document outlines our supported versions and the process for responsibly disclosing vulnerabilities.

---

## Supported Versions

Only the versions listed below receive active security updates. We strongly recommend upgrading to a supported version if you are running an older release.

| Version | Security Support   |
| ------- | ------------------ |
| 2.1     | ✅ Actively supported |
| 2.0     | ✅ Actively supported |
| < 2.0   | ❌ End of life — no security updates |

---

## Reporting a Vulnerability

If you have discovered a security vulnerability in Librewall, please report it promptly. We are committed to investigating all valid reports and will work to remediate confirmed issues as quickly as possible.

### Submission Process

1. Navigate to the **[Issues](../../issues)** tab of this repository.
2. Click **New Issue**.
3. Complete the issue form using the template below.
4. Apply the **`Vulnerability`** label via the right-hand sidebar.
   > **Note:** If you do not have permission to add labels, prefix your issue title with `[VULNERABILITY]`.

---

### Required Information

To help us triage and resolve the issue efficiently, please include the following details in your report:

| Field | Description |
|---|---|
| **Vulnerability Type** | Classification of the issue (e.g., XSS, RCE, Path Traversal, SSRF) |
| **Severity Level** | Estimated impact: `Low` / `Medium` / `High` / `Critical` |
| **Affected Version(s)** | The Librewall version(s) where the issue was observed |
| **Description** | A clear and thorough explanation of the vulnerability and its potential impact |
| **Steps to Reproduce** | A precise, step-by-step sequence to reliably reproduce the issue |
| **Proof of Concept** | Supporting evidence such as screenshots, logs, or code snippets (if applicable) |
| **Suggested Remediation** | Any recommendations for fixing the issue (optional but appreciated) |

---

## Disclosure Policy

- Please **do not disclose the vulnerability publicly** until we have had a reasonable opportunity to investigate and release a fix.
- We aim to acknowledge all reports within **72 hours** and provide a resolution timeline as soon as an initial assessment is complete.
- Once a fix is released, we will credit the reporter (with their consent) in the release notes.

---

## Scope

Reports are most valuable when they address vulnerabilities within the Librewall codebase itself. Issues related to third-party dependencies should be reported upstream to the respective maintainers, though we encourage you to notify us as well so we can track and apply patches accordingly.

---

Thank you for helping keep Librewall secure.

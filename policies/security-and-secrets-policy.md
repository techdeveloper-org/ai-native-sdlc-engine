# Security, Secrets & Vulnerability Management Policy

**Version:** 1.0.0  
**Authority:** `secrets-detection-specialist` (`claude-global-library`)  
**Mandatory Skills:** `devsecops-core`, `application-security-core`, `data-security-privacy-core`  
**Priority:** 🔴 CRITICAL — Pre-Commit & Pre-PR Gate (BLOCKING)  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Zero-Tolerance Mandate

The **AI-Native SDLC Engine** operates under a **Zero-Tolerance Credential & Vulnerability Hygiene Policy**. Autonomous AI agents and automated pipelines are strictly prohibited from generating, staging, committing, or pushing hardcoded secrets, connection credentials, unencrypted tokens, or dependencies with known Critical/High vulnerabilities.

Any confirmed credential exposure or unresolved Critical/High vulnerability results in an immediate **`REJECTED`** pipeline gate verdict with non-zero exit code (`1`).

---

## 2. Credential & Secret Detection Architecture

### 2.1 Multi-Layer Detection Matrix

All code changes, diffs, configuration files, and staged assets are inspected using a three-tier detection engine prior to git commit:

```
Source Code / Diff
       │
       ▼
[Tier 1: High-Entropy Scanner] ── Shannon Entropy H(X) ≥ 4.5 bits/char
       │
       ▼
[Tier 2: Regex Signature Bank] ── TruffleHog v3 + Gitleaks v8 Patterns
       │
       ▼
[Tier 3: Bayesian Scoring]     ── P(Secret | Evidence) ≥ 0.85 → BLOCKED
```

### 2.2 Provider Signature Patterns

The pre-commit scanner intercepts and flags matches against the following provider signatures:

| Target Credential | Signature Pattern / Header | Risk Level |
|---|---|:---:|
| **AWS Access Key ID** | `AKIA[0-9A-Z]{16}` | 🔴 Critical |
| **AWS Secret Access Key** | High-entropy 40-character base64 strings | 🔴 Critical |
| **GCP Service Account** | JSON blocks containing `"type": "service_account"` and `"private_key"` | 🔴 Critical |
| **GitHub Personal Token** | `ghp_[a-zA-Z0-9]{36}`, `ghs_[a-zA-Z0-9]{36}`, `github_pat_[a-zA-Z0-9_]{82}` | 🔴 Critical |
| **Stripe Live API Key** | `sk_live_[0-9a-zA-Z]{24,}`, `rk_live_[0-9a-zA-Z]{24,}` | 🔴 Critical |
| **Twilio Account SID / Token** | `AC[a-z0-9]{32}` and companion auth tokens | 🟠 High |
| **SendGrid API Key** | `SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}` | 🟠 High |
| **Private Keys (PEM)** | `-----BEGIN [A-Z ]*PRIVATE KEY-----` | 🔴 Critical |
| **Database DSN Strings** | `(postgres|mysql|mongodb|redis)://[^\s:]+:[^\s@]+@[^\s/]+` | 🔴 Critical |
| **JWT Secrets / Bearer** | Unencrypted signed JWT tokens matching `eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+` | 🟠 High |

---

## 3. Mathematical Classification & Scoring

### 3.1 Shannon Entropy Threshold

Every candidate token extracted from strings, literals, and environment variables is evaluated using character entropy:

$$H(X) = -\sum_{i=1}^{n} p_i \log_2(p_i)$$

Where $p_i$ is the observed frequency of character class $i$ across the token character set:
- Tokens with $H(X) \ge 4.5\text{ bits/char}$ are classified as high-entropy candidates.
- Hexadecimal strings with $H(X) \ge 3.0\text{ bits/char}$ are classified as high-entropy hashes.

### 3.2 Bayesian Posterior Probability Scoring

Candidate strings are scored using Bayesian posterior inference to distinguish genuine credentials from random test hashes:

$$P(\text{Secret} \mid \text{Entropy}, \text{Regex}) = \frac{P(\text{Entropy}, \text{Regex} \mid \text{Secret}) \cdot P(\text{Secret})}{P(\text{Entropy}, \text{Regex})}$$

**Decision Rule:**
- If $P(\text{Secret} \mid \text{Evidence}) \ge 0.85$, the finding is marked **`VERIFIED_LIKELY`** and the pipeline triggers a hard gate stop.
- If $P(\text{Secret} \mid \text{Evidence}) < 0.50$, the token is deemed low risk and logged for telemetry only.

---

## 4. Dependency Vulnerability (CVE) Governance

1. **Manifest Inspection**:
   - `pom.xml` (Java / Maven)
   - `package.json` / `package-lock.json` (TypeScript / JavaScript)
   - `requirements.txt` / `pyproject.toml` (Python)
   - `go.mod` (Go)
2. **Threshold Blocker**:
   - **CVSS Score $\ge 7.0$ (High / Critical)**: Zero tolerance. PR build is blocked until patched or replaced.
   - **Known Exploited Vulnerabilities (KEV)**: Any CVE cataloged in CISA KEV triggers immediate rejection regardless of CVSS score.
3. **Automated Remediations**:
   - The engine attempts automated semver patch updates (e.g., bumping `1.2.3` to `1.2.4`) and runs test suites to verify zero regression.

---

## 5. Protected Assets & Path Hygiene

### 5.1 Strictly Protected Paths
Autonomous agents are strictly blocked from staging, committing, or pushing:
- `.env`, `.env.*` (Environment configuration files)
- `*.pem`, `*.key`, `*.pfx`, `*.p12` (Cryptographic certificates and keys)
- `id_rsa`, `id_ed25519` (SSH private keys)
- `credentials.json`, `service-account.json` (Cloud service credentials)

### 5.2 Cross-Platform Sanitization
- All security scanner configuration files, file references, and ignore patterns must strictly use **normalized forward slashes (`/`)**.
- Security report outputs must be encoded in **UTF-8 with strict LF (`\n`) line endings**.

---

## 6. Real-World Enforcement Scenarios

### Scenario A: Accidental Hardcoded API Key
- **Context**: An LLM agent generates integration code for Stripe payments and writes:
  ```python
  stripe.api_key = "sk_test_mock_token_for_documentation_only"
  ```
- **Policy Action**: Pre-commit hook runs Tier 2 regex and Tier 1 entropy scans. Both fire. $P(\text{Secret}) = 0.98$.
- **Result**: The commit is aborted immediately. Error printed:
  ```
  [SECURITY GATE VIOLATION] Staged file src/payment.py contains a verified Stripe Live Key.
  Remediation: Use os.getenv('STRIPE_API_KEY') and add mock to test fixture.
  ```

### Scenario B: Transitive Dependency CVE
- **Context**: A feature adds a legacy JSON parser library that carries CVE-2023-XXXX (CVSS 8.5).
- **Policy Action**: Dependency vulnerability gate intercepts PR creation, detects CVSS $\ge 7.0$, and aborts PR submission until the library is replaced with an actively maintained alternative.

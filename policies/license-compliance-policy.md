# Open-Source License & Dependency Compliance Policy

**Version:** 1.0.0  
**Authority:** `compliance-automation-engineer` (`claude-global-library`)  
**Mandatory Skills:** `compliance-management-core`, `legal-data-privacy-core`  
**Priority:** 🔴 CRITICAL — Pre-Commit & Pre-PR Gate (BLOCKING)  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Legal Guardrails

The **AI-Native SDLC Engine** operates on commercial, enterprise, and MIT-licensed software codebases. Autonomous agents frequently introduce third-party libraries without evaluating their legal licensing terms.

To prevent **viral copyleft contamination, license incompatibility, and intellectual property infringement**, all dependencies introduced or upgraded by the engine MUST strictly adhere to this policy.

---

## 2. License Compatibility Taxonomy

Every third-party dependency (npm, pip, maven, gradle, cargo, go) is classified into three legal categories:

### Category A: Permissive (STRICTLY ALLOWED ✅)
Permissive licenses allow commercial use, modification, distribution, and relicensing without imposing copyleft obligations on the host software:
- **MIT License**
- **Apache License 2.0**
- **BSD 2-Clause / 3-Clause**
- **ISC License**
- **The Unlicense / CC0-1.0**

### Category B: Weak Copyleft (CONDITIONAL ⚠️)
Allowed ONLY when consumed as an unmodified, dynamically-linked external library. Embedding or modifying source code directly is strictly prohibited:
- **LGPL-2.1 / LGPL-3.0** (Dynamic linking only; no static bundling in proprietary binaries)
- **Mozilla Public License 2.0 (MPL-2.0)**
- **Eclipse Public License (EPL-1.0 / EPL-2.0)**

### Category C: Strong Copyleft & Source-Available (STRICTLY PROHIBITED ❌)
Viral licenses that mandate that any software linking to, incorporating, or executing alongside them must publish its entire proprietary source code under the same license:
- **GPL-2.0 / GPL-3.0** (GNU General Public License)
- **AGPL-3.0** (Affero General Public License — viral over network APIs)
- **SSPL** (Server Side Public License)
- **Non-Commercial / CC-BY-NC** licenses (Prohibited in commercial environments)

---

## 3. Automated Dependency License Auditing

### 3.1 Verification Triggers
Whenever an autonomous agent modifies:
- `pom.xml` / `build.gradle` (Java)
- `package.json` / `pnpm-lock.yaml` (JavaScript/TypeScript)
- `requirements.txt` / `pyproject.toml` (Python)
- `go.mod` (Go)

The pipeline executes an automated dependency license scan prior to committing:
```bash
# Python
pip-licenses --format=json --output-file=licenses.json

# JavaScript
license-checker --json --out licenses.json
```

### 3.2 Gate Enforcement Decision
- **Pass**: All dependencies belong to Category A (or compliant Category B).
- **Fail / Blocked**: If any dependency belongs to Category C, the pipeline immediately aborts PR creation, removes the offending package from manifests, and prompts the agent to select an Apache 2.0 or MIT alternative.

---

## 4. Software Bill of Materials (SBOM) Generation

During Step 7 (Documentation & Release Packaging), the engine automatically synthesizes an industry-standard SBOM:
- **Formats**: CycloneDX (JSON) and SPDX (JSON).
- **Contents**: Full list of direct and transitive dependencies, package hashes, component versions, and verified licenses.
- Output saved to: `target/sbom.cyclonedx.json` or `dist/sbom.spdx.json`.

---

## 5. Real-World Enforcement Scenarios

### Scenario A: Viral GPL Contamination Prevented
- **Context**: An agent needs an image manipulation library in a Python service and adds `gpl-image-filter` (licensed under GPL-3.0).
- **Policy Action**: The license audit scanner identifies the GPL-3.0 license.
- **Result**: The PR is blocked with the message:
  ```
  [LICENSE COMPLIANCE VIOLATION] Package 'gpl-image-filter' is licensed under GPL-3.0.
  Strong copyleft licenses are strictly forbidden in this repository.
  Action: Replace with an MIT or Apache 2.0 alternative (e.g., 'Pillow').
  ```

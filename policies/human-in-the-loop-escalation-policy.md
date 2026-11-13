# Human-in-the-Loop Escalation & Safety Guardrails Policy

**Version:** 1.0.0  
**Authority:** `harness-engineering-architect` (`claude-global-library`)  
**Mandatory Skills:** `agent-loop-lifecycle-core`, `gate-calibration-scoring-core`, `stop-condition-budget-control-core`  
**Priority:** 🔴 CRITICAL — Pipeline STOP Gates & Safety Boundaries  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Calibration Philosophy

The **AI-Native SDLC Engine** balances high-throughput autonomous execution with rock-solid production safety. 

Rather than imposing a uniform, slow human wait at every trivial step, the harness uses a calibrated approach:
- **Machine-Checkable Gates**: Auto-approved when verified evidence clears statistical confidence thresholds.
- **High-Risk Irreversible Operations**: MUST HALT and demand interactive human confirmation.
- **Headless CI/CD Environments**: Deterministically fail-safe (`ABORT / REJECTED`) on escalation rather than hanging indefinitely.

---

## 2. Gate Auto-Approve Confidence Score (GACS)

For pipeline phases with machine-checkable evidence (e.g., test coverage, API contract verification), the harness computes a composite confidence score:

$$GACS = \left(S_{\text{loss}} \cdot S_{RS} \cdot S_{\text{cov}} \cdot S_{\text{con}}\right)^{1/4}$$

Where:
- $S_{\text{loss}}$: Expected loss survival probability ($1 - p_{\text{defect}}$).
- $S_{RS}$: Composite reliability score of the producing agent roster.
- $S_{\text{cov}}$: Machine-checkable coverage ratio (e.g., test coverage $\ge 80\%$, API contract coverage $\ge 85\%$).
- $S_{\text{con}}$: Multi-agent consensus agreement score among reviewing subagents.

### The Floor & Threshold Decision Rule:
```
IF any of {S_loss, S_RS, S_cov, S_con} < 0.50:
    Decision := ESCALATE  (Hard floor rule: a single failing factor cannot be masked)
ELSE:
    Decision := AUTO-APPROVE   IF GACS ≥ 0.85
                ESCALATE       OTHERWISE
```

---

## 3. Non-Bypassable Hard Human Escalation Triggers

Regardless of any computed confidence score, the pipeline **MUST HALT IMMEDIATELY** and require interactive human sign-off when any of the following 5 triggers occur:

1. **Destructive Database / Infrastructure Commands**:
   - `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `ALTER TABLE ... DROP COLUMN`.
   - `rm -rf /`, deleting root directory trees, destroying cloud infrastructure.
2. **Public API Contract Breaking Changes**:
   - Deleting or renaming existing public API routes, changing request/response JSON field types.
3. **Core Interface / Shared Architecture Mutations**:
   - Modifying shared cross-service interfaces, changing authentication schemas, altering core JWT payload structures.
4. **Budget & Spend Cap Breaches**:
   - Any single task requesting more than **$5.00 USD** in LLM spend.
5. **Production Deployment & Release Gates**:
   - Merging into `production` or `release` branches.

---

## 4. Headless CI/CD Deterministic Fallback Rules

When the pipeline executes headlessly in automated environments (GitHub Actions, Jenkins, Docker containers, cron jobs) where **NO interactive TTY terminal is present**:
1. **Immediate Fail-Safe**:
   - If `CI=true` or stdin is not a TTY, the pipeline **DOES NOT HANG INDEFINITELY**.
   - Any trigger requiring manual confirmation immediately transitions to **`ABORT / REJECTED`** with **exit code `1`**.
2. **Actionable Step Summary**:
   - The harness writes a rich Markdown summary to `$GITHUB_STEP_SUMMARY` / CI console detailing:
     - Exact escalation trigger fired.
     - Affected file and lines.
     - Concrete manual command required to approve or resume.
3. **Interactive Timeout**:
   - In interactive developer workstations, human prompts time out after **10 minutes**, defaulting to safe abort if unacknowledged.

---

## 5. Real-World Enforcement Scenarios

### Scenario A: High-Risk DDL Intercepted
- **Action**: Agent generates code containing `DROP TABLE legacy_orders;`.
- **Harness Action**: Hard Trigger #1 fires. GACS calculation is skipped.
- **Interactive Terminal**:
  ```
  🚨 [NON-BYPASSABLE HUMAN ESCALATION GATE]
  Operation: DROP TABLE legacy_orders
  Target: Production Database
  Risk: Irreversible data loss.
  Do you approve this operation? [y/N]:
  ```
  Execution freezes safely until the developer enters `y`.

### Scenario B: Headless CI/CD Execution
- **Action**: Same `DROP TABLE` command fires inside a GitHub Actions runner.
- **Harness Action**: Headless detection recognizes `CI=true` and no interactive TTY.
- **Result**: Pipeline aborts in 0 seconds with exit code `1`, logs diagnostic error, and prevents CI build hang.

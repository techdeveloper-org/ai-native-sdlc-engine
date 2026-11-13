# Automated Risk Evaluation & Fallback Policy

**Version:** 2.0.0 (Reframed from Proactive Consultation)  
**Authority:** `harness-engineering-architect` (`claude-global-library`)  
**Mandatory Skills:** `agent-routing-dispatch-policy-core`, `gate-calibration-scoring-core`  
**Priority:** 🔴 HIGH — Automated Architectural Routing  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Evolution

Historically, earlier versions of the engine relied on interactive prompts (`AskUserQuestion`) for medium-complexity decisions. However, in automated CI/CD pipelines, Docker containers, and LangGraph subprocesses, **interactive user consultation is impossible and causes hanging builds**.

This policy formalizes the **Automated Risk Evaluation & Fallback Matrix**, replacing manual mid-pipeline questions with deterministic architectural risk scoring, call-graph blast radius analysis, and standardized fallback ladders.

---

## 2. Quantitative Risk Scoring Matrix

Every incoming task and proposed architectural change is evaluated on a **Risk Scale of 1 to 10** based on three objective factors:

$$R = 0.4 \cdot C_{\text{task}} + 0.4 \cdot B_{\text{blast}} + 0.2 \cdot S_{\text{security}}$$

Where:
- $C_{\text{task}}$: Task complexity score (1 to 10 based on files affected).
- $B_{\text{blast}}$: Call graph blast radius (number of downstream callers/services).
- $S_{\text{security}}$: Security sensitivity score (presence of auth, payments, database DDL).

### 2.1 The Three Risk Routing Zones

```
[Risk 1 - 3: Low Risk]      ──► Automated Fast-Path (Execute directly with standard linters)
[Risk 4 - 7: Medium Risk]   ──► Deterministic Architectural Standards (Auto-resolved via rules)
[Risk 8 - 10: High Risk]    ──► HITL Escalation Gate (Mandatory human approval required)
```

| Risk Level | Score | Pipeline Action | Fallback Strategy |
|:---:|:---:|---|---|
| **Low Risk** | **1–3** | Automated fast-path execution. Zero human interruption. | If build fails, auto-revert to clean git commit. |
| **Medium Risk** | **4–7** | Automatically resolved by querying `~/.claude/rules/` and `claude-global-library` standards. | If conflicting patterns exist, select the safer conservative convention (e.g., standard DTO over entity exposure). |
| **High Risk** | **8–10** | Hard STOP. Triggers `policies/human-in-the-loop-escalation-policy.md`. | In headless CI/CD, timeout immediately defaults to safe `ABORT` (exit code 1). |

---

## 3. Decision Traceability & Logging

Every automated architectural decision made by the engine is recorded in `flow-trace.json` with:
- Risk score calculation breakdown ($C_{\text{task}}, B_{\text{blast}}, S_{\text{security}}$).
- Governing standard rule cited from `policies/` or `~/.claude/rules/`.
- Concrete rationale and fallback ladder selected.

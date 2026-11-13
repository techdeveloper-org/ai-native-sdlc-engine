# Universal Pipeline Execution Lifecycle Policy

**Version:** 2.0.0 (Modernized from Hook System)  
**Authority:** `solution-architect` (`claude-global-library`)  
**Mandatory Skills:** `clean-architecture`, `agent-loop-lifecycle-core`  
**Priority:** 🔴 CRITICAL — Pipeline Topology & State Transitions  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Universal Execution Model

Earlier engine iterations relied exclusively on Claude Code CLI hooks (`UserPromptSubmit`, `PreToolUse`, `PostToolUse`). In v2.0.0+, the architecture was fundamentally upgraded to a **Universal, Hook-Free, Model-Agnostic LangGraph StateGraph**.

This policy governs the universal lifecycle of pipeline execution across all modalities:
- **CLI Terminal**: Direct execution via `scripts/3-level-flow.py` and `scripts/cli.py`.
- **Docker & Kubernetes**: Containerized microservices.
- **Headless CI/CD**: GitHub Actions and Jenkins automated runners.
- **IDE & Claude Plugin**: Interactive slash commands.

---

## 2. Universal 3-Level State Machine Topology

The engine executes tasks through three sequential lifecycle levels with explicit state checkpoints:

```
[Task Input]
     │
     ▼
[Level 0: Pre-Flight Guard] ────────► Unicode sanitization, BOM stripping, Windows path normalization
     │
     ▼
[Level 1: Context & State Sync] ────► Task complexity scoring [1-25], token budgeting, session isolation
     │
     ▼
[Level 2: SDLC Execution Core] ─────► 9 Active Steps (CallGraph -> Plan -> Issue -> Branch -> Code ->
                                       Triad Tests -> SonarQube Auto-Fix -> PR Review -> Docs & Release)
     │
     ▼
[Shipped Zero-Debt PR & Audit Log]
```

---

## 3. Interceptor Lifecycle & Safety Boundaries

Instead of external shell hooks, the engine coordinates through **Python LangGraph State Nodes** and **Node Decorators** (`@verify_node`):

1. **Pre-Execution Guards**:
   - `preflight_guard/nodes.py`: Intercepts inputs, strips invalid encodings, and normalizes delimiters.
   - Evaluates budget ceilings before dispatching LLM calls.
2. **In-Flight Tool Mediation**:
   - Validates tool arguments against JSON schemas.
   - Intercepts destructive actions and enforces `policies/human-in-the-loop-escalation-policy.md`.
3. **Post-Execution State Verification**:
   - Verifies tests pass and SonarQube quality gates are satisfied before allowing transition to PR creation.
   - Runs `git status` verification to ensure no untracked artifacts or residue remain.

---

## 4. Error Handling & Circuit Breaking
- Every state node is wrapped with localized error boundaries.
- Transient network failures trigger jittered exponential backoff (max 3 retries).
- Systemic unrecoverable failures trigger clean rollbacks, persist session diagnostics to `flow-trace.json`, and emit structured exit codes.

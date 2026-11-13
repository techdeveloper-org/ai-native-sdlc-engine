# LLM Cost, Token Budget & Runaway Loop Prevention Policy

**Version:** 1.0.0  
**Authority:** `llm-cost-optimizer` (`claude-global-library`)  
**Mandatory Skills:** `token-economics-core`, `llm-performance-math-core`, `genai-procurement-decision-core`  
**Priority:** 🔴 CRITICAL — Runtime & Per-Turn Gate (BLOCKING)  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Cost-Per-Task Governance

Autonomous agentic systems can rapidly exhaust LLM API budgets if trapped in recursive self-correction loops, repeated file reads, or over-verbose token emissions.

The **AI-Native SDLC Engine** enforces strict mathematical token economics:
- **Cost-Per-Successful-Task (CPST)** is the primary metric, not raw token cost.
- Hard, non-bypassable spend caps are enforced per task and per session.
- Output token emission is constrained via Level 2.2 Docstrings-Only standards.
- Runaway auto-fix loops are terminated via strict convergence limits.

---

## 2. Hard Spend Caps & Circuit Breakers

### 2.1 Budget Allocation Tiers

| Scope | Hard Limit (USD) | Warning Threshold | Enforcement Mechanism |
|---|:---:|:---:|---|
| **Single Task / PR** | **$2.00** | 80% ($1.60) | Halts subagent turn. Emits warning. |
| **Full Session (Multi-Task)** | **$10.00** | 80% ($8.00) | Trips Session Circuit Breaker. Persists state checkpoint. |
| **Emergency Global Cap** | **$25.00** | 90% ($22.50) | Immediate hard termination of all running agent threads. |

Configurable via `.env` variables:
- `SDLC_TASK_MAX_BUDGET_USD=2.00`
- `SDLC_SESSION_MAX_BUDGET_USD=10.00`

### 2.2 Circuit Breaker State Machine

```
   [Normal Operation] ── (Spend < 80%) ──► Continues Execution
           │
     (Spend ≥ 80%)
           ▼
   [Warning State]    ── Log telemetry alert, restrict to Haiku/Flash
           │
     (Spend ≥ 100%)
           ▼
[CIRCUIT BREAKER TRIP] ── Hard STOP, persist state checkpoint, escalate to human
```

---

## 3. SonarQube & AST Auto-Fixer 3-Iteration Convergence Limit

To prevent runaway token burns caused by cyclic code repairs (where fixing one Sonar smell triggers another):
1. **Hard Limit**: Maximum **3 consecutive auto-fix iterations per file**.
2. **Convergence Rule**:
   - If a file does not achieve Zero Debt after 3 repair cycles, the auto-fix loop MUST immediately terminate.
   - The file is tagged `CONVERGENCE_LIMIT_EXCEEDED` and marked for manual developer attention.
   - Under no circumstances is an agent permitted to enter a 4th repair cycle on the same file in a single task.

---

## 4. Token Pricing Asymmetry & Emission Discipline

### 4.1 5× Asymmetry Rule
Across all top-tier foundation models (Claude Sonnet, GPT-4o), **output tokens cost approximately 5× more than input tokens** (e.g., $15.00/M output vs $3.00/M input).
- **Enforcement**: Agents MUST NOT emit narrative conversational chatter, line-by-line file read commentary, or chatty apologies.
- All code must comply with **Level 2.2 Docstrings-Only**: strict contract docstrings on public interfaces, zero inline conversational narration.

### 4.2 Prompt-Cache Optimization
- Static prompt prefixes (system instructions, tool definitions, standards catalogs) must remain byte-identical across calls to leverage prompt caching.
- Caching reads yield a **90% discount** ($0.30/M vs $3.00/M on Sonnet).

---

## 5. Model Cascading & Complexity Routing

Tasks must be routed to the most cost-effective model that satisfies the task SLA:

| Task Complexity Tier | Typical Operations | Target Model Family | Blended Cost / M |
|:---:|---|---|:---:|
| **Tier 1 (Trivial / Low)** | Typos, docstrings, formatting, unit test templates | Claude Haiku 4.5 / Gemini Flash / Ollama Local | ~$1.00 |
| **Tier 2 (Medium)** | Standard feature CRUD, DTO mappings, bug fixes | Claude Sonnet 4.6 / GPT-4o | ~$3.00–$5.00 |
| **Tier 3 (High / Critical)** | Multi-file architecture refactoring, AST call graph analysis | Claude Opus 4.7 / GPT-4o Advanced | ~$10.00–$15.00 |

---

## 6. Runaway Turn Cap

- **Disjunctive Stop Predicate**: Every subagent loop must enforce a maximum turn limit of **15 turns**.
- If a subagent has executed 15 turns without completing the task criteria, the harness terminates the subagent and returns control to the orchestrator.

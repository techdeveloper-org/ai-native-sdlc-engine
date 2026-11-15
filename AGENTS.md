# AI-Native SDLC Framework: Universal Multi-Agent Specification

> **Audience:** AI Agents, Subagents, Autonomous Coding Assistants, and Engineers
> **Framework:** AI-Native SDLC Engine (Model-Agnostic, Zero-Debt by Construction)
> **Supported LLM Ecosystems:** Google Gemini / Antigravity, Anthropic Claude, OpenAI / ChatGPT, Ollama (Local), Cursor, Copilot, Windsurf.

---

## 1. Architectural Philosophy

The **AI-Native SDLC Framework** is designed to transform autonomous coding agents from single-shot snippet generators into an **autonomous engineering squad in a box**.

Instead of writing code directly into repositories without verification, every participating agent interacts with the framework through structured contracts:
1. **Pre-Flight Guards & Archaeology**: Call-graph impact analysis across Python, Java, TypeScript, and Kotlin before touching lines of code.
2. **Deterministic Context Isolation**: Dual-path resolution (`~/.sdlc` primary, `~/.claude` legacy fallback, or project-local `./data/`).
3. **Multi-Model Strategic Inference**: Seamless routing and fallback across Google Gemini, Anthropic Claude, OpenAI, and Ollama.
4. **Autonomous Zero-Debt Quality Gates**: Continuous SonarQube static analysis, AST auto-remediation, and triad test generation (positive, negative, edge-case).

---

## 2. Multi-Provider LLM Configuration

The framework dynamically resolves the optimal LLM provider at runtime via `sdlc_engine.llm.llm_call`:

| Provider | Identifier | Required Credentials / Endpoint | Fast Tier | Balanced Tier | Deep Tier |
|:---|:---|:---|:---|:---|:---|
| **Google Gemini** | `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-pro` |
| **Anthropic Claude** | `anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5` | `claude-sonnet-4-6` | `claude-opus-4-6` |
| **OpenAI / ChatGPT** | `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | `gpt-4o` | `o3-mini` / `o1` |
| **Claude Code CLI** | `claude_cli` | `claude` binary on `PATH` | `haiku` | `sonnet` | `opus` |
| **Local Ollama** | `ollama` | `OLLAMA_HOST` (default: `http://localhost:11434`) | `llama3.2` | `qwen2.5-coder` | `deepseek-r1` |

### Environment Variable Overrides
```bash
# Provider selection strategy
export LLM_PROVIDER=auto                       # auto | gemini | anthropic | openai | claude_cli | ollama
export LLM_FALLBACK="anthropic,openai,ollama"  # Priority fallback chain

# Model overrides per tier
export GEMINI_MODEL_FAST="gemini-2.5-flash"
export GEMINI_MODEL_DEEP="gemini-2.5-pro"
export OPENAI_MODEL_FAST="gpt-4o-mini"
export OPENAI_MODEL_DEEP="o3-mini"
export OLLAMA_HOST="http://localhost:11434"
```

---

## 3. Path Resolution & Storage Hierarchy

All file storage, logging, sessions, and memory locations are governed strictly through `sdlc_engine.shared.utils.path_resolver`:

1. **Framework Home:**
   - Evaluates `SDLC_HOME` > `CLAUDE_HOME` > `~/.sdlc/` > `~/.claude/`.
2. **Session Data Root:**
   - Evaluates `SDLC_DATA_DIR` > `AI_NATIVE_SDLC_ENGINE_DATA_DIR` > `CLAUDE_WORKFLOW_ENGINE_DATA_DIR` > `~/.sdlc/memory` > `./data/`.
3. **Logs & Diagnostics:**
   - Evaluates `SDLC_LOGS_DIR` > `CLAUDE_LOGS_DIR` > `{HOME}/logs/`.
4. **Skills & Agents Directory:**
   - Evaluates `SDLC_SKILLS_DIR` / `SDLC_AGENTS_DIR` > `CLAUDE_SKILLS_DIR` / `CLAUDE_AGENTS_DIR` > Global Library / `{HOME}/skills/`.

---

## 4. CLI Execution Commands

For both humans and agent runners:

```bash
# Check system and multi-model provider health
sdlc health

# Run pipeline on a task in analysis/prompt mode (Steps 0-7)
sdlc run "Refactor authentication service to support OAuth2 tokens" --dry-run

# Run full end-to-end SDLC pipeline (Steps 0-14, including GitHub issue & PR)
sdlc run --task "Implement universal retry policy in llm_call" --mode full

# Check current pipeline status and recent sessions
sdlc status

# System diagnostics and MCP checks
sdlc doctor
```

---

## 5. Agent Orchestration Protocol

When executing as a subagent or autonomous agent squad:
1. **Never write unverified code:** Always run archaeology scans (`sdlc_engine.analysis.code_explorer` and `code_graph_analyzer`) before editing.
2. **Follow Level 2.2 Docstrings-Only:** Every public class and method must have contract docstrings; inline comments are banned for routine line narration.
3. **Triad Testing:** Always verify changes with positive, negative, and edge-case unit test suites.
4. **Adhere to Zero-Debt:** If SonarQube or static analysis flags issues, use the `sonar_auto_fixer` loop to resolve them automatically.

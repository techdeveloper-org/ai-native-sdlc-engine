# Unified Tool Optimization & Context Preservation Policy

**Version:** 2.0.0 (Consolidated)  
**Authority:** `token-optimizer-expert` (`claude-global-library`)  
**Mandatory Skills:** `token-economics-core`, `tool-call-mediation-core`  
**Priority:** 🔴 HIGH — Runtime Tool Execution Interceptor  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Purpose

The **Unified Tool Optimization Policy** establishes deterministic parameter limits, AST-first symbol navigation, and context-caching rules for all tool calls executed by the AI-Native SDLC Engine. 

By prioritizing structural indexing over broad text scans and restricting read payloads, this policy achieves **60% to 85% token consumption reduction** per task.

---

## 2. Hard Tool Parameter Constraints

Every tool invocation dispatched by an agent is intercepted and validated against these hard parameter limits:

| Tool Category | Parameter | Maximum Limit | Rationale & Failure Action |
|---|---|:---:|---|
| **File Reading** | `read_max_lines` | **800 lines** | Prevents flooding the context window with massive files. Requires chunked reading via `ByteOffset` / `StartLine`. |
| **File Reading** | `read_max_bytes` | **46,080 bytes (45 KB)** | Memory budget per read call. |
| **File Reading** | `cache_after_n_reads` | **3 reads** | Automatically caches file metadata and structural outline after 3rd read of the same file. |
| **Search / Grep** | `grep_max_matches` | **50 matches** | Prevents dumping thousands of irrelevant text matches into context. |
| **Search / Grep** | `grep_max_results` | **100 total** | Cumulative match cap across all grep calls in a turn. |
| **Web / Docs Search** | `search_max_results` | **10 results** | Enforces focused search retrieval. |
| **Directory Navigation** | `find_max_depth` | **3 levels** | Prevents recursive traversal of `node_modules` or `.git`. |

---

## 3. The Structure-First Navigation Mandate

Autonomous agents MUST follow the **Structure-First Navigation Protocol**:

```
1. Directory Outline (find / list_dir) ──► Understand directory tree layout first (saves 90% tokens)
       │
       ▼
2. AST Symbol Lookup (code graph)     ──► Jump directly to target class / function definition
       │
       ▼
3. Chunked Targeted Read (view_file)  ──► Read ONLY the specific 50-100 line method block needed
```

### Prohibited Anti-Patterns:
- ❌ **Blind Repo-Wide Grep**: Running `grep -r "auth"` across the entire repository without path filtering (consumes 5,000+ tokens).
- ❌ **Whole-File Ingestion**: Reading 3,000-line monolithic files in a single unconstrained call.
- ❌ **Redundant Repeated Reads**: Reading the identical file range multiple times in the same turn without code changes.

---

## 4. AST Navigation vs Raw Grep

When searching for code definitions, agents MUST prioritize AST index tools (`ast_navigate_code` or `code_graph_analyzer`) over raw full-text grep:
- **AST Symbol Lookup**: Resolves class hierarchies, callers, andCallees in ~100 tokens with 100% precision.
- **Raw Text Grep**: Dumps comments, test fixtures, build artifacts, and strings consuming thousands of tokens.

---

## 5. Cross-Platform Sanitization
- All file paths supplied to tools MUST use **normalized forward slashes (`/`)** on all operating systems.
- Shell command executions on Windows must chain with `;` instead of `&&`.

# Performance Benchmarking & Regression Guard Policy

**Version:** 1.0.0  
**Authority:** `performance-testing-engineer` (`claude-global-library`)  
**Mandatory Skills:** `performance-testing-core`, `test-automation-architecture-core`  
**Priority:** 🔴 CRITICAL — Post-Implementation & Pre-PR Gate (BLOCKING)  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Zero-Regression Objective

The **AI-Native SDLC Engine** treats software performance as a first-class engineering contract. Autonomous code changes must not degrade latency percentiles, inflate CPU consumption, introduce memory leaks, or worsen algorithmic Big-O complexity.

Any pull request that introduces an unverified performance regression beyond strict statistical thresholds is **BLOCKED** from merging.

---

## 2. Quantitative Performance Gate Criteria

Every pull request that modifies business logic, database queries, network calls, or serialization must pass automated performance benchmarks against historical baselines:

| Metric | SLA Threshold | Measurement Method | Failure Action |
|---|:---:|---|:---:|
| **$p95$ Latency Regression** | $\le 	ext{baseline} 	imes 1.05$ (max +5%) | Microbenchmark or synthetic load | 🔴 Block PR |
| **$p99$ Latency Regression** | $\le 	ext{baseline} 	imes 1.10$ (max +10%) | HDR Histogram percentiles | 🔴 Block PR |
| **Error Rate Under Load** | $\le 0.1\%$ | 100 concurrent virtual users | 🔴 Block PR |
| **Throughput (TPS)** | $\ge 	ext{baseline} 	imes 0.95$ (max -5%) | Sustained 3-minute load test | 🔴 Block PR |
| **Memory Leak (Soak Test)** | $dM/dt 	o 0$ | 10-minute sustained load soak | 🔴 Block PR |
| **Algorithmic Complexity** | No $O(N) 	o O(N^2)$ regressions | AST loop depth & query analysis | 🔴 Block PR |

---

## 3. Memory Leak & Soak Testing Standards

Memory leaks often escape short unit tests. For microservices and long-running daemons:
1. **Soak Duration**: 10-minute sustained load run using synthetic traffic.
2. **Heap Stability Rule**:
   - Memory consumption must stabilize after the warm-up phase (first 2 minutes).
   - If heap memory increases monotonically ($dM/dt > 0$) without garbage collection reclamation, the test flags a **`POTENTIAL_MEMORY_LEAK`** and blocks the build.

---

## 4. Algorithmic Complexity Degradation Gate

1. **AST Loop Analysis**:
   - The AST parser checks loop depths and query placements.
   - **Banned Anti-Pattern: N+1 Database Queries**: Placing database queries (`findById`, `repository.get()`, SQL queries) inside loops over collections.
2. **Complexity Guard**:
   - Transforming an $O(N)$ hash lookup into an $O(N^2)$ nested iteration over arrays is rejected by pre-PR static analysis.

---

## 5. Automated HDR Histogram Diff Reporting

When performance benchmarks execute, the engine captures latency using **High Dynamic Range (HDR) Histograms** to avoid percentile distortion:
- Generates a latency comparison table attached directly to the PR:
  ```markdown
  ### ⚡ Performance Benchmark Comparison
  | Metric | Baseline | This PR | Delta | Status |
  |---|:---:|:---:|:---:|:---:|
  | p50 | 12.4 ms | 12.1 ms | -2.4% | ✅ PASSED |
  | p95 | 45.2 ms | 46.1 ms | +1.9% | ✅ PASSED (≤ 5%) |
  | p99 | 89.0 ms | 91.2 ms | +2.4% | ✅ PASSED (≤ 10%) |
  | TPS | 1,450 | 1,462 | +0.8% | ✅ PASSED |
  ```

---

## 6. Real-World Enforcement Scenarios

### Scenario A: N+1 Query in Loop
- **Context**: A developer changes an order processing loop to query customer details inside `for order in orders: db.get_customer(order.customer_id)`.
- **Policy Action**: Microbenchmark test detects latency exploding from 35ms to 480ms under 500 orders.
- **Result**: PR is blocked with the finding:
  ```
  [PERFORMANCE GATE REJECTED] N+1 Query Anti-Pattern detected in OrderService.java:142.
  Latency regressed by +1,270% (Baseline: 35ms, Observed: 480ms).
  Remediation: Use batch fetch 'customerRepository.findAllByIdIn(customerIds)'.
  ```

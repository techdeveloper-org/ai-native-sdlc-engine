# Documentation Index

Every document in this repository lives under `docs/`, grouped by functional domain and SDLC phase.
The repository root carries strictly only the four canonical documentation files permitted by `rules/11-documentation-files.md`: `README.md`, `CLAUDE.md`, `SRS.md`, `CHANGELOG.md` (and `VERSION`).

| Folder | Contains | Files |
|---|---|---|
| [`api/`](api/) | API specifications | 1 |
| [`architecture/`](architecture/) | Architecture decisions, ADRs and design prompts | 14 |
| [`contributing/`](contributing/) | Contribution guidelines and community standards | 2 |
| [`guides/`](guides/) | How-to guides, checklists and operational runbooks | 15 |
| [`phase-0-requirements/`](phase-0-requirements/) | Requirements, PRD v2, sequencing & scorecards | 7 |
| [`phase-0-reverse-engineering/`](phase-0-reverse-engineering/) | As-built PRD, call graphs and reverse-engineering artefacts | 25 |
| [`phase-1-architecture/`](phase-1-architecture/) | Phase 1 high-level design and consensus artefacts | 9 |
| [`phase-2-validation/`](phase-2-validation/) | Cross-validation, v2 HLD and consensus reviews | 13 |
| [`phase-5-srs/`](phase-5-srs/) | SRS update report | 1 |
| [`phase-5-uml/`](phase-5-uml/) | CallGraph coverage and diagram reports | 4 |
| [`phase-6-sprint/`](phase-6-sprint/) | Sprint delivery plan and sequencing risk analysis | 4 |
| [`phase-7-routing/`](phase-7-routing/) | Issue routing table and agent capability gap specifications | 4 |
| [`phase-8-alignment/`](phase-8-alignment/) | Premise-staleness scans and implementation readiness report | 4 |
| [`releases/`](releases/) | Per-release requirements and transformation design briefs | 1 |
| [`reports/`](reports/) | System audits, telemetry investigations, and performance reports | 26 |

---

## `architecture/` — Architecture & Design

Architecture Decision Records (ADRs), execution models, and master orchestration prompts.

<details><summary>14 file(s)</summary>

- [adr-002-call-graph-intelligence.md](architecture/adr-002-call-graph-intelligence.md)
- [adr-003-runtime-verification-decorator.md](architecture/adr-003-runtime-verification-decorator.md)
- [adr-004-opt-in-default.md](architecture/adr-004-opt-in-default.md)
- [adr-005-no-llm-in-verifier.md](architecture/adr-005-no-llm-in-verifier.md)
- [adr-006-hook-free-execution.md](architecture/adr-006-hook-free-execution.md)
- [integration-architecture-audit.md](architecture/integration-architecture-audit.md)
- [l3-subgraph-collapse-impact-map.md](architecture/l3-subgraph-collapse-impact-map.md)
- [master-sdlc-orchestration-prompt.md](architecture/master-sdlc-orchestration-prompt.md)
- [orchestration-prompt-v2.1-generic-rules.md](architecture/orchestration-prompt-v2.1-generic-rules.md)
- [permanent-architecture-solution.md](architecture/permanent-architecture-solution.md)
- [pipeline-architecture-overview.md](architecture/pipeline-architecture-overview.md)
- [policies-and-scripts-execution-flow.md](architecture/policies-and-scripts-execution-flow.md)
- [policy-chain-flowcharts.md](architecture/policy-chain-flowcharts.md)
- [remediation-closeout-prompt.md](architecture/remediation-closeout-prompt.md)

</details>

---

## `guides/` — How-to Guides & Runbooks

Operational runbooks, setup walkthroughs, and testing instructions.

<details><summary>15 file(s)</summary>

- [adr-020-push-gate-verification-guide.md](guides/adr-020-push-gate-verification-guide.md)
- [computer-use-preflight-checklist.md](guides/computer-use-preflight-checklist.md)
- [deployment-guide.md](guides/deployment-guide.md)
- [documentation-templates-reference.md](guides/documentation-templates-reference.md)
- [fr17-entry-point-verification-guide.md](guides/fr17-entry-point-verification-guide.md)
- [fr31-uninstall-residue-verification-guide.md](guides/fr31-uninstall-residue-verification-guide.md)
- [fr8-hook-retention-verification-guide.md](guides/fr8-hook-retention-verification-guide.md)
- [getting-started-guide.md](guides/getting-started-guide.md)
- [mcp-tools-reference-guide.md](guides/mcp-tools-reference-guide.md)
- [nfr11-lifecycle-verification-guide.md](guides/nfr11-lifecycle-verification-guide.md)
- [parallel-execution-quick-guide.md](guides/parallel-execution-quick-guide.md)
- [stale-call-graph-runbook.md](guides/stale-call-graph-runbook.md)
- [testing-guide.md](guides/testing-guide.md)
- [troubleshooting-guide.md](guides/troubleshooting-guide.md)
- [uninstall-residue-runbook.md](guides/uninstall-residue-runbook.md)

</details>

---

## `reports/` — Investigations & Audits

Audits, performance measurements, memory analysis, and engineering reports.

<details><summary>26 file(s)</summary>

- [anthropic-feedback-and-training-insights.md](reports/anthropic-feedback-and-training-insights.md)
- [auto-fix-enforcement-summary.md](reports/auto-fix-enforcement-summary.md)
- [auto-sync-policies-implementation.md](reports/auto-sync-policies-implementation.md)
- [capability-disposition-ledger.md](reports/capability-disposition-ledger.md)
- [context-read-enforcement-audit.md](reports/context-read-enforcement-audit.md)
- [execution-system-fixes-summary.md](reports/execution-system-fixes-summary.md)
- [fr8a-stop-hook-spawn-report.md](reports/fr8a-stop-hook-spawn-report.md)
- [historical-hooks-setup-2026-03-10.md](reports/historical-hooks-setup-2026-03-10.md)
- [home-path-classification-baseline.md](reports/home-path-classification-baseline.md)
- [home-path-classification-report.md](reports/home-path-classification-report.md)
- [implementation-engineering-notes.md](reports/implementation-engineering-notes.md)
- [linter-noqa-audit-backlog.md](reports/linter-noqa-audit-backlog.md)
- [multi-window-session-isolation-fix.md](reports/multi-window-session-isolation-fix.md)
- [nfr1-process-measurement-report.md](reports/nfr1-process-measurement-report.md)
- [policy-implementation-audit-v2.md](reports/policy-implementation-audit-v2.md)
- [prompt-generation-upgrade-summary.md](reports/prompt-generation-upgrade-summary.md)
- [qa-safety-verification-stream1.md](reports/qa-safety-verification-stream1.md)
- [review-checkpoint-consistency-fix.md](reports/review-checkpoint-consistency-fix.md)
- [session-bloat-and-subprocess-leak-analysis.md](reports/session-bloat-and-subprocess-leak-analysis.md)
- [session-id-tracking-system.md](reports/session-id-tracking-system.md)
- [session-management-comparison.md](reports/session-management-comparison.md)
- [step7-documentation-implementation-summary.md](reports/step7-documentation-implementation-summary.md)
- [subpackage-refactoring-plan.md](reports/subpackage-refactoring-plan.md)
- [symbol-naming-audit-report.md](reports/symbol-naming-audit-report.md)
- [test-suite-quality-summary.md](reports/test-suite-quality-summary.md)
- [v2.0.0-review-index.md](reports/v2.0.0-review-index.md)

</details>

---

## `contributing/` — Community & Contribution Guidelines

Code of conduct and contributor guidelines.

<details><summary>2 file(s)</summary>

- [code-of-conduct.md](contributing/code-of-conduct.md)
- [contributing-guide.md](contributing/contributing-guide.md)

*(Note: GitHub issue and PR templates live in `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md`)*

</details>

---

## `phase-0-requirements/` — Requirements & Sequencing

<details><summary>7 file(s)</summary>

- [faithfulness_scorecard_phase0.json](phase-0-requirements/faithfulness_scorecard_phase0.json)
- [hallucination_report_phase0.json](phase-0-requirements/hallucination_report_phase0.json)
- [phase0-faithfulness-summary.md](phase-0-requirements/phase0-faithfulness-summary.md)
- [phase0-hallucination-summary.md](phase-0-requirements/phase0-hallucination-summary.md)
- [phase1-architect-brief.md](phase-0-requirements/phase1-architect-brief.md)
- [prd-v2.0.0.md](phase-0-requirements/prd-v2.0.0.md)
- [product-sequencing-v2.0.0.md](phase-0-requirements/product-sequencing-v2.0.0.md)

</details>

---

## `phase-0-reverse-engineering/` — Reverse-Engineering Artefacts

<details><summary>25 file(s)</summary>

- [api_surface.json](phase-0-reverse-engineering/api_surface.json)
- [as-built-executive-summary.md](phase-0-reverse-engineering/as-built-executive-summary.md)
- [as-built-prd-v1.21.4.md](phase-0-reverse-engineering/as-built-prd-v1.21.4.md)
- [ast_call_graph.json](phase-0-reverse-engineering/ast_call_graph.json)
- [ast-call-graph-summary.md](phase-0-reverse-engineering/ast-call-graph-summary.md)
- [audit_surface.json](phase-0-reverse-engineering/audit_surface.json)
- [builder-divergence-analysis.md](phase-0-reverse-engineering/builder-divergence-analysis.md)
- [capability-loss-analysis.md](phase-0-reverse-engineering/capability-loss-analysis.md)
- [claude-md-drift-analysis.md](phase-0-reverse-engineering/claude-md-drift-analysis.md)
- [codebase_kg/](phase-0-reverse-engineering/codebase_kg/)
- [codebase-knowledge-graph.md](phase-0-reverse-engineering/codebase-knowledge-graph.md)
- [complexity_report.json](phase-0-reverse-engineering/complexity_report.json)
- [dead_code_report.json](phase-0-reverse-engineering/dead_code_report.json)
- [dead-code-archaeology-summary.md](phase-0-reverse-engineering/dead-code-archaeology-summary.md)
- [impact_analysis_graph.json](phase-0-reverse-engineering/impact_analysis_graph.json)
- [impact-analysis-summary.md](phase-0-reverse-engineering/impact-analysis-summary.md)
- [lhs.json](phase-0-reverse-engineering/lhs.json)
- [path-violations-audit.md](phase-0-reverse-engineering/path-violations-audit.md)
- [policy_corpus_inventory.json](phase-0-reverse-engineering/policy_corpus_inventory.json)
- [policy_enforcement_raw.json](phase-0-reverse-engineering/policy_enforcement_raw.json)
- [policy-code-contradictions.md](phase-0-reverse-engineering/policy-code-contradictions.md)
- [policy-corpus-summary.md](phase-0-reverse-engineering/policy-corpus-summary.md)
- [policy-enforcement-summary.md](phase-0-reverse-engineering/policy-enforcement-summary.md)
- [rts_selection.json](phase-0-reverse-engineering/rts_selection.json)
- [stop-hook-overhead-analysis.md](phase-0-reverse-engineering/stop-hook-overhead-analysis.md)
- [structural_inventory_summary.md](phase-0-reverse-engineering/structural-inventory-summary.md)

</details>

---

## `phase-1-architecture/` — Architecture Synthesis

<details><summary>9 file(s)</summary>

- [consensus_verdict_phase1.json](phase-1-architecture/consensus_verdict_phase1.json)
- [faithfulness_scorecard_phase1.json](phase-1-architecture/faithfulness_scorecard_phase1.json)
- [feasibility_analysis.json](phase-1-architecture/feasibility_analysis.json)
- [hallucination_report_phase1.json](phase-1-architecture/hallucination_report_phase1.json)
- [high-level-design-v1.md](phase-1-architecture/high-level-design-v1.md)
- [phase1-consensus-verdict.md](phase-1-architecture/phase1-consensus-verdict.md)
- [phase1-faithfulness-summary.md](phase-1-architecture/phase1-faithfulness-summary.md)
- [phase1-hallucination-summary.md](phase-1-architecture/phase1-hallucination-summary.md)
- [plugin-schema-spike-report.md](phase-1-architecture/plugin-schema-spike-report.md)

</details>

---

## `phase-2-validation/` — Cross-Validation & v2 HLD

<details><summary>13 file(s)</summary>

- [advisory_items.json](phase-2-validation/advisory_items.json)
- [ba_review.json](phase-2-validation/ba_review.json)
- [consensus_verdict_phase2.json](phase-2-validation/consensus_verdict_phase2.json)
- [faithfulness_scorecard_phase2.json](phase-2-validation/faithfulness_scorecard_phase2.json)
- [hallucination_report_phase2.json](phase-2-validation/hallucination_report_phase2.json)
- [hallucination_report_sequencing.json](phase-2-validation/hallucination_report_sequencing.json)
- [high-level-design-v2.md](phase-2-validation/high-level-design-v2.md)
- [phase2-consensus-verdict.md](phase-2-validation/phase2-consensus-verdict.md)
- [phase2-faithfulness-summary.md](phase-2-validation/phase2-faithfulness-summary.md)
- [phase2-hallucination-summary.md](phase-2-validation/phase2-hallucination-summary.md)
- [pm_review.json](phase-2-validation/pm_review.json)
- [sa_defence.json](phase-2-validation/sa_defence.json)
- [sequencing-hallucination-summary.md](phase-2-validation/sequencing-hallucination-summary.md)

</details>

---

## `phase-5-srs/` — SRS Lifecycle Record

<details><summary>1 file(s)</summary>

- [srs-update-report.md](phase-5-srs/srs-update-report.md)

</details>

---

## `phase-5-uml/` — Probes & Diagrams

<details><summary>4 file(s)</summary>

- [callgraph-coverage-probe.md](phase-5-uml/callgraph-coverage-probe.md)
- [discovery_manifest.json](phase-5-uml/discovery_manifest.json)
- [drawio-diagrams-generation-report.md](phase-5-uml/drawio-diagrams-generation-report.md)
- [mermaid-diagrams-generation-report.md](phase-5-uml/mermaid-diagrams-generation-report.md)

</details>

---

## `phase-6-sprint/` — Sprint Delivery Plan

<details><summary>4 file(s)</summary>

- [delivery-sprint-plan.md](phase-6-sprint/delivery-sprint-plan.md)
- [github_issues.json](phase-6-sprint/github_issues.json)
- [issue_key_map.json](phase-6-sprint/issue_key_map.json)
- [sprint-sequencing-risks.md](phase-6-sprint/sprint-sequencing-risks.md)

</details>

---

## `phase-7-routing/` — Issue-to-Agent Routing

<details><summary>4 file(s)</summary>

- [agent-capability-gaps.md](phase-7-routing/agent-capability-gaps.md)
- [issue-agent-routing-table.md](phase-7-routing/issue-agent-routing-table.md)
- [library-agent-gap-specification.md](phase-7-routing/library-agent-gap-specification.md)
- [routing_map.json](phase-7-routing/routing_map.json)

</details>

---

## `phase-8-alignment/` — Pre-Implementation Alignment

<details><summary>4 file(s)</summary>

- [blockers.json](phase-8-alignment/blockers.json)
- [implementation-readiness-report.md](phase-8-alignment/implementation-readiness-report.md)
- [premise_scan_bh.json](phase-8-alignment/premise_scan_bh.json)
- [premise-staleness-scan-report.md](phase-8-alignment/premise-staleness-scan-report.md)

</details>

---

## `releases/` — Release Notes & Briefs

<details><summary>1 file(s)</summary>

- [v2.0.0-plugin-requirements-brief.md](releases/v2.0.0-plugin-requirements-brief.md)

</details>

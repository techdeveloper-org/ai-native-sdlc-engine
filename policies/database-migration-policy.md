# Database Schema Migration & Backward Compatibility Policy

**Version:** 1.0.0  
**Authority:** `database-engineer` (`claude-global-library`)  
**Mandatory Skills:** `database-schema-migration-core`, `rdbms-core`, `clean-architecture`  
**Priority:** 🔴 CRITICAL — Pre-Implementation & Pre-PR Gate (BLOCKING)  
**Status:** 🟢 ENFORCED & ACTIVE  

---

## 1. Executive Summary & Zero-Downtime Objective

In modern microservices and distributed systems, application deployments follow rolling or canary rollout patterns. At any given moment during a deployment, **Version $N$ (old code) and Version $N+1$ (new code) run concurrently against the same shared database**.

Therefore, the **AI-Native SDLC Engine** mandates that all database schema changes MUST be strictly **backward-compatible, non-blocking, and zero-downtime by construction**.

---

## 2. The Expand-Contract (Parallel Change) Pattern

Any schema change that alters existing columns, moves data, or deprecates structures MUST follow the formal three-phase compatibility state machine:

```
[Phase 1: EXPAND] ──────► Add new column/table as nullable or with default.
                           Application dual-writes to OLD + NEW, reads from OLD.
                           (Rolling deploy: Both Version N and N+1 remain healthy)
       │
       ▼
[Phase 2: MIGRATE] ─────► Throttled background backfill of historical rows.
                           Switch application reads to NEW schema. Continue dual-writing.
       │
       ▼
[Phase 3: CONTRACT] ────► Verify 100% traffic on NEW schema over N+1 releases.
                           Safely drop or archive the OLD schema column/table.
```

---

## 3. Strictly Prohibited Production DDL Operations

The following database operations cause full-table locks, replication lag, or instant application crashes during rolling deployments and are **STRICTLY PROHIBITED** in a single migration step:

| Prohibited Operation | Failure Mechanism & Blast Radius | Required Zero-Downtime Alternative |
|---|---|---|
| **Direct `DROP COLUMN`** | Version $N$ pods executing `SELECT *` or referencing the column immediately throw fatal `500 Internal Server Errors`. | Keep old column intact. Mark `@Deprecated`. Drop only in release $N+1$ after all callers are removed. |
| **`NOT NULL` without `DEFAULT`** | Postgres / MySQL rewrites the full table while holding an exclusive lock, blocking all production reads and writes. | Add column as nullable first (`NULL`). Backfill existing rows with defaults. Alter column to `NOT NULL` in Phase 3. |
| **Renaming a Column Directly** | Breaks all running queries expecting the old column name. | Add the new column (Expand), dual-write, migrate historical data, and drop old column later. |
| **Unindexed Foreign Keys** | Updates or deletes on parent tables trigger full-table sequential scans and lock contention on the child table. | Concurrently create an index on the foreign key column (`CREATE INDEX CONCURRENTLY`) before attaching the constraint. |
| **Large Table DDL without Online Tools** | Full table rewrite on tables with $>100,000$ rows causes operational downtime. | Use online DDL tools (`gh-ost`, `pt-online-schema-change`, or `pg_repack`). |

---

## 4. Throttled Backfill Throughput Standards

When migrating historical records from old columns/tables to new structures:
- **Batch Size Limit**: Backfill jobs MUST operate in bounded batches of **$\le 1,000$ rows per transaction**.
- **Sleep Delay**: Every batch transaction MUST sleep for a minimum of $50\text{ms}$ to allow database replication threads to catch up and prevent replication lag.
- **Lock Timeout**: Every DDL migration script MUST explicitly configure a strict lock timeout:
  ```sql
  -- PostgreSQL
  SET lock_timeout = '5s';
  SET statement_timeout = '30s';
  ```
  If the migration cannot acquire a lock within 5 seconds, it must abort cleanly rather than queuing production traffic behind an exclusive lock.

---

## 5. Mandatory Rollback & Idempotency Rules

1. **Companion Undo Scripts**:
   Every versioned migration `V__<timestamp>__<feature>.sql` MUST have an accompanying, automated, tested rollback script `U__<timestamp>__<feature>.sql`.
2. **Idempotency**:
   All migration scripts must use idempotent guards:
   - `IF NOT EXISTS` for table and column creation.
   - `IF EXISTS` for drops.
3. **Framework Standards**:
   Migrations must use established enterprise versioning tools:
   - **Java / Spring Boot**: Flyway or Liquibase.
   - **Python / FastAPI**: Alembic.
   - **Node.js / TypeScript**: Prisma Migrate or TypeORM.

---

## 6. Real-World Enforcement Scenarios

### Scenario A: Renaming User Attribute
- **Requirement**: Rename `phone_number` to `mobile_e164` across the database.
- **Prohibited Approach**: `ALTER TABLE users RENAME COLUMN phone_number TO mobile_e164;`
- **Enforced Approach**:
  1. Add `mobile_e164 VARCHAR(32) NULL;` (Release $N$).
  2. Model writes to both `phone_number` and `mobile_e164`.
  3. Throttled migration script copies data from `phone_number` to `mobile_e164`.
  4. Application switches reads to `mobile_e164` (Release $N+1$).
  5. Remove `phone_number` column (Release $N+2$).

### Scenario B: Foreign Key Addition
- **Requirement**: Link `order_items.order_id` to `orders.id`.
- **Policy Action**: Pipeline AST analysis checks whether `order_items(order_id)` has an index. If missing, the migration is rejected with instructions to include `CREATE INDEX CONCURRENTLY idx_order_items_order_id ON order_items(order_id);` before declaring the constraint.

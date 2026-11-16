---
name: postgres-query-tuner
description: Tune slow PostgreSQL SQL queries, review EXPLAIN ANALYZE execution plans, and suggest B-tree indexes to eliminate sequential scans.
---

# Postgres Query Tuner (Overlap Pair Fixture B)

Tune PostgreSQL SQL queries using `EXPLAIN ANALYZE` execution plans and index recommendations.

## Use when

- The user has a slow PostgreSQL SQL query or `EXPLAIN ANALYZE` plan and needs composite B-tree index recommendations, sequential scan elimination, or join tuning.

## Do not use when

- Writing marketing copy.

## Workflow

1. Inspect the PostgreSQL `EXPLAIN ANALYZE` plan for sequential scans and expensive joins.
2. Propose composite B-tree indexes and rewritten predicates.

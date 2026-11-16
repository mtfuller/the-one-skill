---
name: sql-query-optimizer
description: Analyze slow PostgreSQL SQL queries, inspect EXPLAIN ANALYZE execution plans, and recommend composite B-tree indexes.
---

# SQL Query Optimizer (Overlap Pair Fixture A)

Optimize slow PostgreSQL SQL queries by inspecting `EXPLAIN ANALYZE` plans and index usage.

## Use when

- The user shares a slow PostgreSQL SQL query or `EXPLAIN ANALYZE` plan and wants index recommendations, sequential scan elimination, or join order tuning.

## Do not use when

- Editing frontend CSS stylesheets.

## Workflow

1. Parse the SQL query and `EXPLAIN ANALYZE` output to identify sequential scans and high-cost nested loops.
2. Recommend targeted B-tree or covering indexes.

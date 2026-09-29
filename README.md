# Data Quality Checks

A command-line tool for validating datasets before they enter a pipeline.
Checks are declared in YAML and executed as SQL against the data. The tool
exits non-zero if any fail, so it can gate a CI job or a scheduled load.

## Usage

    python src/runner.py data.parquet -c checks.yml
    echo $?   # 0 = all passed, 1 = at least one failed

## Available checks

| Check | Arguments | Verifies |
|---|---|---|
| row_count | min | Table has at least N rows |
| not_null | column | No null values |
| unique | column | No duplicate values |
| unique_composite | columns | No duplicates across a composite key |
| in_range | column, min, max | Values fall within bounds |
| accepted_values | column, values | Values come from a known set |

## Design

Each check is a function taking a database connection and returning a
CheckResult. Checks are registered in a dict, so adding one means writing a
function and adding a single line. The runner is never modified.

Checks are SQL rather than pandas operations, pushing work to the database
instead of pulling rows into Python.

## Tests

    python -m pytest tests/ -v

Tests run against a small in-memory table with known-bad rows, verifying each
check detects the problem it targets and reports the correct count.

## Limitations

- Column names are interpolated into SQL rather than parameterized, since SQL
  cannot parameterize identifiers. This is an injection risk if configs come
  from untrusted sources; production would validate against the information
  schema first.
- Single-table only, no cross-table referential integrity.
- No run history, so no drift detection between loads.
- DuckDB and parquet only.

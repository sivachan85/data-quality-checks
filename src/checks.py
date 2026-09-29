"""Data quality checks expressed as SQL, run against DuckDB."""
from dataclasses import dataclass
from typing import Any

import duckdb


@dataclass
class CheckResult:
    name: str
    column: str | None
    passed: bool
    failing_rows: int
    detail: str

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        target = f"{self.column}" if self.column else "(table)"
        return f"[{status}] {self.name:<16} {target:<20} {self.detail}"


def not_null(con, table: str, column: str, **_: Any) -> CheckResult:
    n = con.execute(
        f'SELECT count(*) FROM {table} WHERE "{column}" IS NULL'
    ).fetchone()[0]
    return CheckResult("not_null", column, n == 0, n, f"{n} null values")


def unique(con, table: str, column: str, **_: Any) -> CheckResult:
    n = con.execute(f"""
        SELECT coalesce(sum(c), 0) FROM (
            SELECT count(*) AS c FROM {table}
            GROUP BY "{column}" HAVING count(*) > 1
        )
    """).fetchone()[0]
    return CheckResult("unique", column, n == 0, n, f"{n} duplicate rows")


def in_range(con, table, column, min=None, max=None, **_: Any) -> CheckResult:
    clauses = []
    if min is not None:
        clauses.append(f'"{column}" < {min}')
    if max is not None:
        clauses.append(f'"{column}" > {max}')
    where = " OR ".join(clauses) or "FALSE"
    n = con.execute(
        f'SELECT count(*) FROM {table} WHERE "{column}" IS NOT NULL AND ({where})'
    ).fetchone()[0]
    return CheckResult("in_range", column, n == 0, n,
                       f"{n} rows outside [{min}, {max}]")


def accepted_values(con, table, column, values=(), **_: Any) -> CheckResult:
    listed = ", ".join(f"'{v}'" for v in values)
    n = con.execute(
        f'SELECT count(*) FROM {table} '
        f'WHERE "{column}" IS NOT NULL AND "{column}" NOT IN ({listed})'
    ).fetchone()[0]
    return CheckResult("accepted_values", column, n == 0, n,
                       f"{n} unexpected values")


def row_count(con, table, min=None, **_: Any) -> CheckResult:
    n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    ok = n >= (min or 0)
    return CheckResult("row_count", None, ok, 0 if ok else 1,
                       f"{n:,} rows (minimum {min:,})")


REGISTRY = {
    "not_null": not_null,
    "unique": unique,
    "in_range": in_range,
    "accepted_values": accepted_values,
    "row_count": row_count,
}


def unique_composite(con, table: str, columns=(), **_: Any) -> CheckResult:
    """Uniqueness across a combination of columns (a composite key)."""
    cols = ", ".join(f'"{c}"' for c in columns)
    n = con.execute(f"""
        SELECT coalesce(sum(c), 0) FROM (
            SELECT count(*) AS c FROM {table}
            GROUP BY {cols} HAVING count(*) > 1
        )
    """).fetchone()[0]
    label = "+".join(columns)
    return CheckResult("unique_composite", label, n == 0, n,
                       f"{n} duplicate rows on ({label})")


REGISTRY["unique_composite"] = unique_composite

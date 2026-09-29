"""Unit tests for individual data quality checks."""
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from checks import not_null, unique, in_range, accepted_values, row_count


@pytest.fixture
def con():
    c = duckdb.connect()
    c.execute("""
        CREATE TABLE dataset AS SELECT * FROM (VALUES
            (1, 'a', 10),
            (2, 'b', 20),
            (3, NULL, 30),
            (3, 'c', 999)
        ) AS t(id, label, value)
    """)
    return c


def test_not_null_detects_nulls(con):
    r = not_null(con, "dataset", "label")
    assert not r.passed
    assert r.failing_rows == 1


def test_not_null_passes_clean_column(con):
    assert not_null(con, "dataset", "id").passed


def test_unique_detects_duplicates(con):
    r = unique(con, "dataset", "id")
    assert not r.passed
    assert r.failing_rows == 2


def test_in_range_flags_outlier(con):
    r = in_range(con, "dataset", "value", min=0, max=100)
    assert not r.passed
    assert r.failing_rows == 1


def test_in_range_ignores_nulls(con):
    con.execute("INSERT INTO dataset VALUES (5, 'd', NULL)")
    assert in_range(con, "dataset", "value", min=0, max=1000).passed


def test_accepted_values(con):
    r = accepted_values(con, "dataset", "label", values=["a", "b"])
    assert not r.passed
    assert r.failing_rows == 1


def test_row_count_minimum(con):
    assert row_count(con, "dataset", min=4).passed
    assert not row_count(con, "dataset", min=5).passed

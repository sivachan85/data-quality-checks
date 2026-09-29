"""Run a YAML-defined suite of data quality checks against a dataset."""
import argparse
import sys
from pathlib import Path

import duckdb
import yaml

from checks import REGISTRY


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_suite(data_path: str, config: dict) -> list:
    con = duckdb.connect()
    con.execute(
        f"CREATE VIEW dataset AS SELECT * FROM read_parquet('{data_path}')"
    )
    results = []
    for spec in config.get("checks", []):
        spec = dict(spec)
        kind = spec.pop("check")
        fn = REGISTRY.get(kind)
        if fn is None:
            raise ValueError(f"unknown check type: {kind}")
        results.append(fn(con, "dataset", **spec))
    return results


def main() -> int:
    p = argparse.ArgumentParser(description="Run data quality checks.")
    p.add_argument("data", help="path to a parquet file")
    p.add_argument("-c", "--config", required=True, help="YAML check suite")
    args = p.parse_args()

    results = run_suite(args.data, load_config(Path(args.config)))

    for r in results:
        print(r)

    failed = [r for r in results if not r.passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

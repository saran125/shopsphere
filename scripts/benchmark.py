"""Run measured, repeatable demo-store workloads and write CSV results."""
import argparse
import csv
import time
from pathlib import Path

from shopsphere.document_store import DocumentStore
from shopsphere.sql_store import SQLStore


def measure(label: str, function, repeats: int) -> list[dict[str, float | str]]:
    for _ in range(2):
        function()
    rows = []
    for run in range(1, repeats + 1):
        started = time.perf_counter()
        function()
        elapsed = (time.perf_counter() - started) * 1000
        rows.append({"workload": label, "run": run, "milliseconds": round(elapsed, 4)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/benchmark_results.csv"))
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    sql = SQLStore()
    documents = DocumentStore()
    for product in sql.catalogue():
        for _ in range(3):
            documents.record_view(0, product["product_id"])
    workloads = [
        measure("sql_catalogue", lambda: sql.catalogue(), args.repeats),
        measure("document_top_viewed", documents.top_viewed, args.repeats),
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["workload", "run", "milliseconds"])
        writer.writeheader()
        for rows in workloads:
            writer.writerows(rows)
    print(f"Wrote measured timings to {args.output}")


if __name__ == "__main__":
    main()

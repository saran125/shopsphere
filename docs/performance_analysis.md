# Performance methodology

Run `python -m shopsphere.scripts.benchmark --repeats 30`. The script performs two warm-up
runs and writes actual timings to `data/benchmark_results.csv`; it does not
fabricate results. Record Python version, operating system, dataset size,
indexes and whether services are local before interpreting results.

The SQL workload uses indexed relational catalogue joins. The document workload
groups browsing events in memory in demo mode; a service comparison should use
the equivalent MongoDB aggregation in `db/mongodb_store.py`. Results are
environment-specific and must not be generalized from one run.

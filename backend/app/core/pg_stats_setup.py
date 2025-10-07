"""
PostgreSQL pg_stat_statements monitoring setup and query scripts.

This module helps identify:
- Slow queries
- N+1 query patterns
- Most frequently executed queries
- Query performance metrics

Usage:
    # Enable extension (run as superuser)
    python -m app.core.pg_stats_setup --enable

    # View query statistics
    python -m app.core.pg_stats_setup --top-slow 10
    python -m app.core.pg_stats_setup --most-frequent 20
    python -m app.core.pg_stats_setup --reset
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text


def enable_pg_stat_statements() -> None:
    """
    Enable pg_stat_statements extension in PostgreSQL.
    Must be run as superuser or with appropriate permissions.
    """
    with SessionLocal() as db:
        try:
            # Check if extension exists
            result = db.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
                )
            ).scalar()

            if result:
                print("✅ pg_stat_statements extension already enabled")
            else:
                # Create extension
                db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
                db.commit()
                print("✅ pg_stat_statements extension enabled successfully")

            # Verify configuration
            result = db.execute(
                text("SELECT * FROM pg_stat_statements LIMIT 1")
            ).fetchone()
            print(f"✅ Extension is working - {result}")

        except Exception as e:
            print(f"❌ Error enabling pg_stat_statements: {e}")
            print("\nNote: You may need to add to postgresql.conf:")
            print("  shared_preload_libraries = 'pg_stat_statements'")
            print("  pg_stat_statements.track = all")
            print("Then restart PostgreSQL.")
            raise


def get_slow_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve the slowest queries by mean execution time.

    Args:
        limit: Number of queries to return

    Returns:
        List of query statistics
    """
    query = text(
        """
        SELECT 
            calls,
            total_exec_time,
            mean_exec_time,
            min_exec_time,
            max_exec_time,
            stddev_exec_time,
            rows,
            query
        FROM pg_stat_statements
        ORDER BY mean_exec_time DESC
        LIMIT :limit
    """
    )

    with SessionLocal() as db:
        results = db.execute(query, {"limit": limit}).fetchall()

    queries = []
    for row in results:
        queries.append(
            {
                "calls": row[0],
                "total_time_ms": round(row[1], 2),
                "mean_time_ms": round(row[2], 2),
                "min_time_ms": round(row[3], 2),
                "max_time_ms": round(row[4], 2),
                "stddev_ms": round(row[5], 2),
                "rows": row[6],
                "query": row[7][:200] + "..." if len(row[7]) > 200 else row[7],
            }
        )

    return queries


def get_most_frequent_queries(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve the most frequently executed queries.

    Args:
        limit: Number of queries to return

    Returns:
        List of query statistics
    """
    query = text(
        """
        SELECT 
            calls,
            total_exec_time,
            mean_exec_time,
            rows,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS hit_percent,
            query
        FROM pg_stat_statements
        ORDER BY calls DESC
        LIMIT :limit
    """
    )

    with SessionLocal() as db:
        results = db.execute(query, {"limit": limit}).fetchall()

    queries = []
    for row in results:
        queries.append(
            {
                "calls": row[0],
                "total_time_ms": round(row[1], 2),
                "mean_time_ms": round(row[2], 2),
                "rows": row[3],
                "cache_hit_percent": round(row[4] or 0, 2),
                "query": row[5][:200] + "..." if len(row[5]) > 200 else row[5],
            }
        )

    return queries


def detect_n_plus_one() -> List[Dict[str, Any]]:
    """
    Detect potential N+1 query patterns.
    Identifies similar queries executed many times.

    Returns:
        List of suspected N+1 patterns
    """
    query = text(
        """
        SELECT 
            calls,
            mean_exec_time,
            query
        FROM pg_stat_statements
        WHERE calls > 50  -- Executed more than 50 times
          AND query NOT LIKE '%pg_stat_statements%'
          AND query NOT LIKE '%information_schema%'
        ORDER BY calls DESC
        LIMIT 20
    """
    )

    with SessionLocal() as db:
        results = db.execute(query).fetchall()

    suspects = []
    for row in results:
        if "WHERE" in row[2] or "IN (" in row[2]:
            suspects.append(
                {
                    "calls": row[0],
                    "mean_time_ms": round(row[1], 2),
                    "query": row[2][:200] + "..." if len(row[2]) > 200 else row[2],
                }
            )

    return suspects


def reset_statistics() -> None:
    """Reset pg_stat_statements statistics."""
    with SessionLocal() as db:
        db.execute(text("SELECT pg_stat_statements_reset()"))
        db.commit()
        print("✅ pg_stat_statements statistics reset")


def print_query_report(queries: List[Dict[str, Any]], title: str) -> None:
    """Pretty print query statistics."""
    print(f"\n{'=' * 100}")
    print(f"{title:^100}")
    print(f"{'=' * 100}\n")

    if not queries:
        print("No queries found.")
        return

    for i, q in enumerate(queries, 1):
        print(f"{i}. Calls: {q['calls']:,} | Mean: {q['mean_time_ms']:.2f}ms")
        if "total_time_ms" in q:
            print(f"   Total: {q['total_time_ms']:.2f}ms")
        if "rows" in q:
            print(f"   Rows: {q['rows']:,}")
        if "cache_hit_percent" in q:
            print(f"   Cache Hit: {q['cache_hit_percent']:.1f}%")
        print(f"   Query: {q['query']}")
        print()


def main():
    """CLI entry point for pg_stat_statements management."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL pg_stat_statements monitoring and analysis"
    )
    parser.add_argument(
        "--enable", action="store_true", help="Enable pg_stat_statements extension"
    )
    parser.add_argument(
        "--top-slow",
        type=int,
        metavar="N",
        help="Show top N slowest queries",
    )
    parser.add_argument(
        "--most-frequent",
        type=int,
        metavar="N",
        help="Show top N most frequent queries",
    )
    parser.add_argument(
        "--detect-n-plus-one",
        action="store_true",
        help="Detect potential N+1 query patterns",
    )
    parser.add_argument("--reset", action="store_true", help="Reset query statistics")

    args = parser.parse_args()

    try:
        if args.enable:
            enable_pg_stat_statements()

        if args.top_slow:
            queries = get_slow_queries(args.top_slow)
            print_query_report(queries, f"Top {args.top_slow} Slowest Queries")

        if args.most_frequent:
            queries = get_most_frequent_queries(args.most_frequent)
            print_query_report(
                queries, f"Top {args.most_frequent} Most Frequent Queries"
            )

        if args.detect_n_plus_one:
            suspects = detect_n_plus_one()
            print_query_report(suspects, "Potential N+1 Query Patterns")

        if args.reset:
            reset_statistics()

        if not any(vars(args).values()):
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

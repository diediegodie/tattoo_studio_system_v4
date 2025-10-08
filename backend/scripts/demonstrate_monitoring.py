#!/usr/bin/env python3
"""
Runtime Monitoring Demonstration Script

Demonstrates:
1. Structured logging with JSON output
2. SQLAlchemy query timing and logging
3. Flask request/response tracking
4. pg_stat_statements query analysis
5. N+1 query detection
6. Performance metrics capture

Usage:
    python backend/scripts/demonstrate_monitoring.py
"""

import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from app.core.logging_config import get_logger

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.pg_stats_setup import (
    get_slow_queries,
    get_most_frequent_queries,
    detect_n_plus_one,
    reset_statistics,
)

logger = get_logger(__name__)


def print_section(title: str) -> None:
    """Log formatted section header."""
    logger.info("Section", extra={"context": {"title": title, "delimiter": "=" * 100}})


def test_endpoint(url: str, description: str) -> Dict[str, Any]:
    """
    Test an endpoint and capture metrics.

    Args:
        url: Endpoint URL
        description: Test description

    Returns:
        Response metrics
    """
    logger.info(
        "Testing endpoint", extra={"context": {"description": description, "url": url}}
    )

    start_time = time.time()

    try:
        response = requests.get(url, timeout=30)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms

        logger.info(
            "Endpoint response",
            extra={
                "context": {
                    "status": response.status_code,
                    "elapsed_ms": round(elapsed, 2),
                }
            },
        )

        try:
            data = response.json()
            if isinstance(data, dict):
                logger.info(
                    "Response keys", extra={"context": {"keys": list(data.keys())}}
                )
            elif isinstance(data, list):
                logger.info("Response items", extra={"context": {"count": len(data)}})
        except:
            logger.info(
                "Response length", extra={"context": {"bytes": len(response.text)}}
            )

        return {
            "url": url,
            "status": response.status_code,
            "elapsed_ms": elapsed,
            "success": True,
        }

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(
            "Endpoint error",
            extra={"context": {"error": str(e), "elapsed_ms": round(elapsed, 2)}},
            exc_info=True,
        )

        return {
            "url": url,
            "error": str(e),
            "elapsed_ms": elapsed,
            "success": False,
        }


def demonstrate_structured_logging():
    """Demonstrate structured logging output."""
    print_section("1. STRUCTURED LOGGING DEMONSTRATION")
    logger.info("Example JSON log entries")

    # Simulate log entries
    log_entries = [
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "logger": "app.controllers.extrato_controller",
            "message": "Processando extrato mensal",
            "context": {"mes": 9, "ano": 2025, "user_id": 1},
        },
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "logger": "app.core.logging_config",
            "message": "SQL Query Executed",
            "context": {
                "query": "SELECT * FROM transacao WHERE mes = :mes",
                "duration_ms": 12.34,
                "row_count": 45,
            },
        },
        {
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "logger": "sqlalchemy.engine",
            "message": "SAWarning: Coercing Subquery object into a select()",
            "context": {"file": "extrato_core.py", "line": 156},
        },
    ]

    for entry in log_entries:
        logger.info("Example entry", extra={"context": entry})


def demonstrate_query_logging():
    """Demonstrate SQLAlchemy query logging."""
    print_section("2. SQLALCHEMY QUERY LOGGING")
    logger.info(
        "Queries will be logged with",
        extra={
            "context": {
                "details": [
                    "Full SQL statement with parameters",
                    "Execution time in milliseconds",
                    "Number of rows returned",
                    "Stack trace to calling code",
                ]
            }
        },
    )
    logger.info(
        "Example query log",
        extra={
            "context": {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "logger": "sqlalchemy.engine",
                "message": "Query executed",
                "context": {
                    "sql": "SELECT * FROM agendamentos WHERE data >= :data_inicio AND data <= :data_fim",
                    "params": {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"},
                    "duration_ms": 8.76,
                    "row_count": 23,
                    "caller": "app/controllers/calendar_controller.py:145",
                },
            }
        },
    )


def demonstrate_request_tracking():
    """Demonstrate Flask request/response tracking."""
    print_section("3. FLASK REQUEST/RESPONSE TRACKING")
    logger.info(
        "Each HTTP request logs",
        extra={
            "context": {
                "details": [
                    "Method and path",
                    "Query parameters",
                    "Response status code",
                    "Total processing time",
                    "User context (if authenticated)",
                ]
            }
        },
    )
    logger.info(
        "Example request log",
        extra={
            "context": {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "logger": "app.main",
                "message": "Request completed",
                "context": {
                    "method": "GET",
                    "path": "/extrato/api",
                    "query_params": {"mes": "9", "ano": "2025"},
                    "status_code": 200,
                    "duration_ms": 125.43,
                    "user_id": 1,
                    "ip": "127.0.0.1",
                },
            }
        },
    )


def demonstrate_pg_stats():
    """Demonstrate pg_stat_statements analysis."""
    print_section("4. POSTGRESQL QUERY ANALYSIS (pg_stat_statements)")

    try:
        logger.info("Analyzing query performance")

        # Get slow queries
        logger.info("Slowest Queries")
        slow_queries = get_slow_queries(5)
        if slow_queries:
            for i, q in enumerate(slow_queries, 1):
                logger.info(
                    "Slow query",
                    extra={
                        "context": {
                            "rank": i,
                            "mean_time_ms": round(q["mean_time_ms"], 2),
                            "calls": q["calls"],
                            "query": q["query"],
                        }
                    },
                )
        else:
            logger.info("No queries found (may need to reset stats or execute queries)")

        # Get frequent queries
        logger.info("Most Frequent Queries")
        frequent = get_most_frequent_queries(5)
        if frequent:
            for i, q in enumerate(frequent, 1):
                logger.info(
                    "Frequent query",
                    extra={
                        "context": {
                            "rank": i,
                            "calls": q["calls"],
                            "mean_time_ms": round(q["mean_time_ms"], 2),
                            "cache_hit_percent": round(q["cache_hit_percent"], 1),
                            "query": q["query"],
                        }
                    },
                )
        else:
            logger.info("No queries found")

        # Detect N+1
        logger.info("Potential N+1 Patterns")
        n_plus_one = detect_n_plus_one()
        if n_plus_one:
            for i, q in enumerate(n_plus_one, 1):
                logger.warning(
                    "Potential N+1 pattern",
                    extra={
                        "context": {
                            "rank": i,
                            "calls": q["calls"],
                            "mean_time_ms": round(q["mean_time_ms"], 2),
                            "query": q["query"],
                        }
                    },
                )
        else:
            logger.info("No obvious N+1 patterns detected")

    except Exception as e:
        logger.error(
            "Error accessing pg_stat_statements",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        logger.info(
            "To enable pg_stat_statements",
            extra={
                "context": {
                    "steps": [
                        "Add to postgresql.conf:",
                        "shared_preload_libraries = 'pg_stat_statements'",
                        "pg_stat_statements.track = all",
                        "Restart PostgreSQL",
                        "Run: python -m app.core.pg_stats_setup --enable",
                    ]
                }
            },
        )


def run_live_tests():
    """Run live endpoint tests with monitoring."""
    print_section("5. LIVE ENDPOINT TESTING")

    base_url = "http://127.0.0.1:5000"

    logger.info(
        "Note: Make sure the Flask app is running!",
        extra={"context": {"start_cmd": "python backend/app/main.py"}},
    )

    # Reset pg_stat_statements before testing
    try:
        reset_statistics()
        logger.info("Reset pg_stat_statements")
    except:
        logger.warning("Could not reset pg_stat_statements")

    # Test endpoints
    tests = [
        (f"{base_url}/", "Homepage"),
        (f"{base_url}/extrato/api?mes=9&ano=2025", "Extrato API - September 2025"),
        (f"{base_url}/historico/api", "Historico API"),
        (
            f"{base_url}/calendar/api?start=2025-01-01&end=2025-01-31",
            "Calendar API - January 2025",
        ),
    ]

    results = []
    for url, desc in tests:
        result = test_endpoint(url, desc)
        results.append(result)
        time.sleep(0.5)  # Small delay between requests

    # Summary
    logger.info(
        "Test Summary",
        extra={
            "context": {
                "total": len(results),
                "successful": sum(1 for r in results if r["success"]),
                "failed": len(results) - sum(1 for r in results) if results else 0,
                "avg_response_ms": (
                    round(sum(r["elapsed_ms"] for r in results) / len(results), 2)
                    if results
                    else 0
                ),
            }
        },
    )

    # Analyze queries after tests
    logger.info("Query Analysis After Tests")
    demonstrate_pg_stats()


def main():
    """Main demonstration flow."""
    print_section("RUNTIME MONITORING DEMONSTRATION")
    logger.info(
        "This script demonstrates the monitoring capabilities",
        extra={
            "context": {
                "features": [
                    "Structured logging with JSON format",
                    "SQLAlchemy query timing and logging",
                    "Flask request/response tracking",
                    "pg_stat_statements query analysis",
                    "N+1 query pattern detection",
                    "Performance metrics capture",
                ]
            }
        },
    )

    try:
        # Run demonstrations
        demonstrate_structured_logging()
        demonstrate_query_logging()
        demonstrate_request_tracking()
        demonstrate_pg_stats()

        # Run live tests automatically to avoid interactive input
        run_live_tests()
        logger.info(
            "Demonstration complete",
            extra={
                "context": {
                    "next_steps": [
                        "Start the app: python backend/app/main.py",
                        "Check logs/app.log for JSON logs",
                        "Check console for colored output",
                        "Run: python -m app.core.pg_stats_setup --top-slow 10",
                    ]
                }
            },
        )

    except KeyboardInterrupt:
        logger.warning("Demonstration interrupted")
    except Exception as e:
        logger.error(
            "Demonstration error", extra={"context": {"error": str(e)}}, exc_info=True
        )
        raise


if __name__ == "__main__":
    main()

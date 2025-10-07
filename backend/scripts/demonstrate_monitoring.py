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

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app
from app.core.pg_stats_setup import (
    get_slow_queries,
    get_most_frequent_queries,
    detect_n_plus_one,
    reset_statistics,
)


def print_section(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'=' * 100}")
    print(f"{title:^100}")
    print(f"{'=' * 100}\n")


def test_endpoint(url: str, description: str) -> Dict[str, Any]:
    """
    Test an endpoint and capture metrics.

    Args:
        url: Endpoint URL
        description: Test description

    Returns:
        Response metrics
    """
    print(f"\n🔍 Testing: {description}")
    print(f"   URL: {url}")

    start_time = time.time()

    try:
        response = requests.get(url, timeout=30)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms

        print(f"   ✅ Status: {response.status_code}")
        print(f"   ⏱️  Response Time: {elapsed:.2f}ms")

        try:
            data = response.json()
            if isinstance(data, dict):
                print(f"   📦 Response Keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"   📦 Response Items: {len(data)}")
        except:
            print(f"   📦 Response Length: {len(response.text)} bytes")

        return {
            "url": url,
            "status": response.status_code,
            "elapsed_ms": elapsed,
            "success": True,
        }

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"   ❌ Error: {e}")
        print(f"   ⏱️  Time to Error: {elapsed:.2f}ms")

        return {
            "url": url,
            "error": str(e),
            "elapsed_ms": elapsed,
            "success": False,
        }


def demonstrate_structured_logging():
    """Demonstrate structured logging output."""
    print_section("1. STRUCTURED LOGGING DEMONSTRATION")

    print("📝 Example JSON log entries:")
    print()

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
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print()


def demonstrate_query_logging():
    """Demonstrate SQLAlchemy query logging."""
    print_section("2. SQLALCHEMY QUERY LOGGING")

    print("📊 Queries will be logged with:")
    print("   • Full SQL statement with parameters")
    print("   • Execution time in milliseconds")
    print("   • Number of rows returned")
    print("   • Stack trace to calling code")
    print()

    print("Example query log:")
    print(
        json.dumps(
            {
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
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def demonstrate_request_tracking():
    """Demonstrate Flask request/response tracking."""
    print_section("3. FLASK REQUEST/RESPONSE TRACKING")

    print("📡 Each HTTP request logs:")
    print("   • Method and path")
    print("   • Query parameters")
    print("   • Response status code")
    print("   • Total processing time")
    print("   • User context (if authenticated)")
    print()

    print("Example request log:")
    print(
        json.dumps(
            {
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
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def demonstrate_pg_stats():
    """Demonstrate pg_stat_statements analysis."""
    print_section("4. POSTGRESQL QUERY ANALYSIS (pg_stat_statements)")

    try:
        print("🔍 Analyzing query performance...")
        print()

        # Get slow queries
        print("📉 Slowest Queries:")
        slow_queries = get_slow_queries(5)
        if slow_queries:
            for i, q in enumerate(slow_queries, 1):
                print(
                    f"\n{i}. Mean Time: {q['mean_time_ms']:.2f}ms | Calls: {q['calls']:,}"
                )
                print(f"   Query: {q['query']}")
        else:
            print("   No queries found (may need to reset stats or execute queries)")

        # Get frequent queries
        print("\n\n📈 Most Frequent Queries:")
        frequent = get_most_frequent_queries(5)
        if frequent:
            for i, q in enumerate(frequent, 1):
                print(
                    f"\n{i}. Calls: {q['calls']:,} | Mean: {q['mean_time_ms']:.2f}ms | Cache Hit: {q['cache_hit_percent']:.1f}%"
                )
                print(f"   Query: {q['query']}")
        else:
            print("   No queries found")

        # Detect N+1
        print("\n\n⚠️  Potential N+1 Patterns:")
        n_plus_one = detect_n_plus_one()
        if n_plus_one:
            for i, q in enumerate(n_plus_one, 1):
                print(f"\n{i}. Calls: {q['calls']:,} | Mean: {q['mean_time_ms']:.2f}ms")
                print(f"   Query: {q['query']}")
                print(
                    "   🚨 This pattern suggests N+1 queries - consider eager loading"
                )
        else:
            print("   ✅ No obvious N+1 patterns detected")

    except Exception as e:
        print(f"❌ Error accessing pg_stat_statements: {e}")
        print("\nTo enable pg_stat_statements:")
        print("1. Add to postgresql.conf:")
        print("     shared_preload_libraries = 'pg_stat_statements'")
        print("     pg_stat_statements.track = all")
        print("2. Restart PostgreSQL")
        print("3. Run: python -m app.core.pg_stats_setup --enable")


def run_live_tests():
    """Run live endpoint tests with monitoring."""
    print_section("5. LIVE ENDPOINT TESTING")

    base_url = "http://127.0.0.1:5000"

    print("⚠️  Note: Make sure the Flask app is running!")
    print(f"   Starting server with: python backend/app/main.py")
    print()

    input("Press Enter when server is ready...")

    # Reset pg_stat_statements before testing
    try:
        reset_statistics()
        print("✅ Reset pg_stat_statements\n")
    except:
        print("⚠️  Could not reset pg_stat_statements\n")

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
    print("\n\n📊 Test Summary:")
    successful = sum(1 for r in results if r["success"])
    print(f"   Total Tests: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {len(results) - successful}")
    print(
        f"   Avg Response Time: {sum(r['elapsed_ms'] for r in results) / len(results):.2f}ms"
    )

    # Analyze queries after tests
    print("\n\n🔍 Query Analysis After Tests:")
    demonstrate_pg_stats()


def main():
    """Main demonstration flow."""
    print_section("RUNTIME MONITORING DEMONSTRATION")

    print("This script demonstrates the monitoring capabilities:")
    print("✓ Structured logging with JSON format")
    print("✓ SQLAlchemy query timing and logging")
    print("✓ Flask request/response tracking")
    print("✓ pg_stat_statements query analysis")
    print("✓ N+1 query pattern detection")
    print("✓ Performance metrics capture")
    print()

    try:
        # Run demonstrations
        demonstrate_structured_logging()
        demonstrate_query_logging()
        demonstrate_request_tracking()
        demonstrate_pg_stats()

        # Ask if user wants to run live tests
        print("\n" + "=" * 100)
        response = input("\nRun live endpoint tests? (y/n): ").strip().lower()

        if response == "y":
            run_live_tests()
        else:
            print("\n✅ Demonstration complete!")
            print("\nTo see live logs:")
            print("1. Start the app: python backend/app/main.py")
            print("2. Check logs/app.log for JSON logs")
            print("3. Check console for colored output")
            print("4. Run: python -m app.core.pg_stats_setup --top-slow 10")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demonstration interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()

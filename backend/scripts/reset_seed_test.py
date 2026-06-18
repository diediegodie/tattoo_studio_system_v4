#!/usr/bin/env python3
"""
Reset, seed, and test script for Tattoo Studio Management System.

This script performs the following operations:
1. Resets the database (Docker or local)
2. Seeds test data for current month
3. Runs automated tests
4. Provides clear console output

Usage:
    python scripts/reset_seed_test.py
    # or as Flask CLI command (if configured)
    flask reset-seed-test

Environment Variables:
    HISTORICO_DEBUG=1 - Enable debug logging for historico endpoint
    DOCKER_RESET=1 - Force Docker reset mode
"""

import argparse
import os
import subprocess
import sys
import webbrowser
from datetime import date, datetime
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.base import Base, Client, Comissao, Gasto, Pagamento, Sessao, User
from app.db.session import SessionLocal, engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def detect_environment():
    """Detect if running in Docker or locally."""
    # Check for Docker environment
    if os.getenv("DOCKER_RESET") == "1":
        return "docker"

    # Check if we're inside a Docker container
    if os.path.exists("/.dockerenv"):
        return "docker"

    # Check if docker-compose is available and docker-compose.yml exists
    try:
        subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
        docker_compose_file = backend_dir.parent / "docker-compose.yml"
        if docker_compose_file.exists():
            # Additional check: see if Docker containers are actually running
            result = subprocess.run(
                ["docker-compose", "ps", "-q"],
                cwd=backend_dir.parent,
                capture_output=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Check if we can actually connect to the Docker database
                # For development, prefer local SQLite unless Docker is explicitly requested
                if os.getenv("FORCE_DOCKER_DB") == "1":
                    return "docker"
                else:
                    return "local"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return "local"


def reset_database(env_type):
    """Reset the database."""
    logger.info("Resetting database", extra={"context": {"action": "reset_db"}})

    if env_type == "docker":
        logger.info("Using Docker Compose", extra={"context": {"mode": "docker"}})
        try:
            # Stop and remove containers with volumes
            subprocess.run(
                ["docker-compose", "down", "-v"], cwd=backend_dir.parent, check=True
            )

            # Start only the database
            subprocess.run(
                ["docker-compose", "up", "-d", "db"], cwd=backend_dir.parent, check=True
            )

            logger.info(
                "Database reset complete",
                extra={"context": {"mode": "docker", "status": "ok"}},
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(
                "Docker reset failed",
                extra={"context": {"error": str(e)}},
                exc_info=True,
            )
            return False
    else:
        logger.info(
            "Using local SQLite database",
            extra={"context": {"mode": "local"}},
        )
        try:
            # For local development, use a local SQLite database
            local_db_path = backend_dir.parent / "tattoo_studio_dev.db"
            local_db_url = f"sqlite:///{local_db_path}"

            # Set environment variable to use local database
            os.environ["DATABASE_URL"] = local_db_url

            # Import after setting the environment
            from app.db.base import Base
            from app.db.session import engine as local_engine

            # Drop all tables and recreate
            Base.metadata.drop_all(bind=local_engine)
            Base.metadata.create_all(bind=local_engine)

            logger.info(
                "Database reset complete",
                extra={
                    "context": {
                        "mode": "local",
                        "status": "ok",
                        "db_path": str(local_db_path),
                    }
                },
            )
            return True
        except Exception as e:
            logger.error(
                "Local reset failed",
                extra={"context": {"error": str(e)}},
                exc_info=True,
            )
            return False


def seed_test_data():
    """Seed current month test data."""
    logger.info("Seeding test data", extra={"context": {"action": "seed"}})

    db = SessionLocal()
    try:
        # Clear existing data
        db.query(Comissao).delete()
        db.query(Pagamento).delete()
        db.query(Sessao).delete()
        db.query(Gasto).delete()
        db.query(Client).delete()
        db.query(User).delete()
        db.commit()

        # Create test client and artist
        test_client = Client(name="João Silva", jotform_submission_id="test123")
        test_artist = User()
        test_artist.name = "Ana Tattoo"
        test_artist.email = "ana.tattoo@test.com"
        test_artist.role = "artist"
        db.add(test_client)
        db.add(test_artist)
        db.commit()

        # Use current month date for determinism
        current_date = date.today().replace(day=15)  # Mid-month

        # Create payment
        payment = Pagamento(
            data=current_date,
            valor=500.00,
            forma_pagamento="Cartão de Crédito",
            observacoes="Pagamento teste",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
        )
        db.add(payment)
        db.commit()

        # Create commissions for the payment
        commission1 = Comissao(
            pagamento_id=payment.id,
            artista_id=test_artist.id,
            percentual=70.0,
            valor=350.00,
            observacoes="Comissão teste 1",
        )
        commission2 = Comissao(
            pagamento_id=payment.id,
            artista_id=test_artist.id,
            percentual=112.0,
            valor=560.00,
            observacoes="Comissão teste 2",
        )
        db.add(commission1)
        db.add(commission2)
        db.commit()

        # Create session
        session = Sessao(
            data=current_date,
            valor=800.00,
            observacoes="Sessão teste",
            cliente_id=test_client.id,
            artista_id=test_artist.id,
            status="completed",
        )
        db.add(session)
        db.commit()

        # Create expense
        expense = Gasto(
            data=current_date,
            valor=455.00,
            descricao="Material de tatuagem",
            forma_pagamento="Dinheiro",
            created_by=test_artist.id,
        )
        db.add(expense)
        db.commit()

        logger.info(
            "Test data seeded",
            extra={
                "context": {
                    "counts": {
                        "clientes": 1,
                        "artistas": 1,
                        "pagamentos": 1,
                        "sessoes": 1,
                        "comissoes": 2,
                        "gastos": 1,
                    },
                    "expected_totals": {
                        "receita": 1300.00,
                        "comissoes": 910.00,
                        "despesas": 455.00,
                        "liquida": 390.00,
                    },
                }
            },
        )

        return True

    except Exception as e:
        db.rollback()
        logger.error(
            "Seeding failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False
    finally:
        db.close()


def seed_edge_cases():
    """Seed optional edge case data (in separate months or scenarios)."""
    logger.info(
        "Seeding edge case data",
        extra={"context": {"action": "seed_edge_cases"}},
    )

    # For now, we'll keep it simple and just ensure the main test data is there
    # Additional edge cases can be added as separate test scenarios
    logger.info("Edge cases handled in test suite")
    return True


def run_tests():
    """Run automated tests."""
    logger.info(
        "Running automated tests",
        extra={
            "context": {
                "action": "pytest",
                "file": "tests/integration/test_historico.py",
            }
        },
    )

    try:
        # Set environment for testing
        env = os.environ.copy()
        env["FLASK_ENV"] = "testing"
        env["TESTING"] = "true"
        # Use the same database we set up
        env["DATABASE_URL"] = os.environ.get(
            "DATABASE_URL", f"sqlite:///{backend_dir.parent / 'tattoo_studio_dev.db'}"
        )

        # Run pytest on historico tests and related tests
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_historico.py",
                "-v",
                "--tb=short",
            ],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("All tests passed")
            return True
        else:
            logger.error(
                "Tests failed",
                extra={"context": {"stdout": result.stdout, "stderr": result.stderr}},
            )
            return False

    except Exception as e:
        logger.error(
            "Test execution failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False


def print_debug_logs():
    """Print debug logs if HISTORICO_DEBUG is enabled."""
    if os.getenv("HISTORICO_DEBUG") == "1":
        logger.info("Debug logs from historico endpoint")
        # The debug logs will be printed during test execution
        # This is just a placeholder for additional debug info if needed
        pass


def open_browser():
    """Open the historico page in the default browser."""
    try:
        url = "http://localhost:5000/historico"
        logger.info(
            "Opening in default browser",
            extra={"context": {"url": url}},
        )
        webbrowser.open(url)
        logger.info("Browser opened successfully")
    except Exception as e:
        logger.warning(
            "Could not open browser (this is normal in headless environments)",
            extra={
                "context": {"error": str(e), "url": "http://localhost:5000/historico"}
            },
        )


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Reset, seed, and test Tattoo Studio System"
    )
    parser.add_argument("--skip-reset", action="store_true", help="Skip database reset")
    parser.add_argument("--skip-seed", action="store_true", help="Skip data seeding")
    parser.add_argument("--skip-tests", action="store_true", help="Skip test execution")

    args = parser.parse_args()

    logger.info(
        "Tattoo Studio System - Reset, Seed & Test",
        extra={"context": {"delimiter": "=" * 50}},
    )

    # Detect environment
    env_type = detect_environment()
    logger.info(
        "Environment detected",
        extra={"context": {"env_type": env_type}},
    )

    success = True

    # Step 1: Reset database
    if not args.skip_reset:
        if not reset_database(env_type):
            success = False

    # Step 2: Seed data
    if success and not args.skip_seed:
        if not seed_test_data():
            success = False
        if not seed_edge_cases():
            success = False

    # Step 3: Run tests
    if success and not args.skip_tests:
        if not run_tests():
            success = False

    # Step 4: Print debug logs if enabled
    if success:
        print_debug_logs()

    # Step 5: Open browser if tests passed
    if success and not args.skip_tests:
        open_browser()

    # Final status
    logger.info("Final status", extra={"context": {"delimiter": "=" * 50}})
    if success:
        logger.info(
            "All operations completed successfully",
            extra={
                "context": {
                    "next_steps": [
                        "Visit /historico for current month totals",
                        "Visit /extrato for historical data",
                    ]
                }
            },
        )
        return 0
    else:
        logger.error("Some operations failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

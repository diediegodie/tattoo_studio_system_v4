#!/usr/bin/env python3
"""
Demonstration script for batch processing in atomic extrato generation.

This script shows how the transparent batch processing works without
exposing the complexity to end users.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging_config import get_logger
from app.services.extrato_batch import (
    get_batch_size,
    process_records_in_batches,
)

logger = get_logger(__name__)


def demonstrate_batch_processing():
    """Demonstrate how batch processing works transparently."""
    logger.info(
        "Transparent Batch Processing Demonstration",
        extra={"context": {"section": "intro"}},
    )
    logger.info("=" * 50, extra={"context": {"section": "intro"}})

    # Show current batch size configuration
    batch_size = get_batch_size()
    logger.info(
        "Current batch size",
        extra={
            "context": {
                "batch_size": batch_size,
                "source": "env:BATCH_SIZE",
                "default": 100,
                "min": 1,
            }
        },
    )

    # Demonstrate with sample data
    logger.info("Processing Sample Dataset", extra={"context": {"section": "dataset"}})

    # Simulate processing 23 records in batches
    sample_records = list(range(1, 24))  # Records 1-23
    logger.info(
        "Total records to process",
        extra={"context": {"count": len(sample_records), "records": sample_records}},
    )

    # Process function that simulates work
    def simulate_processing(batch):
        """Simulate processing a batch of records."""
        batch_sum = sum(batch)
        batch_avg = batch_sum / len(batch) if batch else 0
        logger.info(
            "Processing batch",
            extra={
                "context": {
                    "batch": batch,
                    "sum": batch_sum,
                    "avg": round(batch_avg, 2),
                }
            },
        )
        return {"batch": batch, "sum": batch_sum, "count": len(batch), "avg": batch_avg}

    logger.info("Starting batch processing", extra={"context": {"section": "run"}})

    # Process in batches
    batch_results = []
    for result in process_records_in_batches(
        sample_records, batch_size, simulate_processing
    ):
        batch_results.append(result)
    logger.info(
        "Batch completed", extra={"context": {"batch_index": len(batch_results)}}
    )

    # Summary
    total_sum = sum(r["sum"] for r in batch_results)
    avg_per_batch = sum(r["count"] for r in batch_results) / len(batch_results)
    logger.info(
        "Processing Summary",
        extra={
            "context": {
                "total_batches": len(batch_results),
                "total_sum": total_sum,
                "avg_records_per_batch": round(avg_per_batch, 2),
            }
        },
    )

    # Show how this works in the real system
    logger.info(
        "Real system flow",
        extra={"context": {"steps": [1, 2, 3, 4, 5, 6, 7]}},
    )

    # Configuration examples
    logger.info(
        "Configuration Examples",
        extra={
            "context": {
                "examples": [
                    "BATCH_SIZE=50",
                    "BATCH_SIZE=500",
                    "BATCH_SIZE=100 (default)",
                ]
            }
        },
    )

    logger.info(
        "Benefits of Transparent Batch Processing",
        extra={
            "context": {
                "benefits": [
                    "Improved performance",
                    "Reduced memory usage",
                    "Transaction safety",
                    "No user impact",
                    "Configurable",
                    "Testable and maintainable",
                ]
            }
        },
    )


def demonstrate_environment_configuration():
    """Show how batch size can be configured via environment."""
    logger.info(
        "Environment Configuration Demo", extra={"context": {"section": "env_demo"}}
    )

    original_batch_size = os.environ.get("BATCH_SIZE")

    # Test different configurations
    test_configs = [None, "25", "100", "500", "invalid"]

    for config in test_configs:
        if config is None:
            os.environ.pop("BATCH_SIZE", None)
            config_desc = "not set (default)"
        else:
            os.environ["BATCH_SIZE"] = config
            config_desc = f"set to '{config}'"

        batch_size = get_batch_size()
        logger.info(
            "BATCH_SIZE configuration",
            extra={"context": {"desc": config_desc, "batch_size": batch_size}},
        )

    # Restore original configuration
    if original_batch_size is not None:
        os.environ["BATCH_SIZE"] = original_batch_size
    else:
        os.environ.pop("BATCH_SIZE", None)


if __name__ == "__main__":
    demonstrate_batch_processing()
    demonstrate_environment_configuration()

    logger.info(
        "Ready for Production",
        extra={
            "context": {
                "message": "Batch processing active, optimized, and safe",
            }
        },
    )

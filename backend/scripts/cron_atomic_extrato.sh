#!/bin/bash

# Atomic Extrato Generation CRON Script
# This script should be scheduled to run monthly (e.g., 1st of each month at 2 AM)

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_FILE="$PROJECT_ROOT/backend/logs/atomic_extrato_cron.log"
PYTHON_SCRIPT="$SCRIPT_DIR/run_atomic_extrato.py"

# Environment setup
export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
cd "$PROJECT_ROOT/backend"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Main execution
log "=== Starting Atomic Extrato CRON Job ==="

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    log "ERROR: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    log "✓ Virtual environment activated"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    log "✓ Virtual environment activated"
else
    log "WARNING: No virtual environment found, using system Python"
fi

# Run the atomic extrato generation
log "Running atomic extrato generation..."
python "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

# Check exit code
if [ $? -eq 0 ]; then
    log "✓ Atomic extrato generation completed successfully"
else
    log "✗ Atomic extrato generation failed with exit code $?"
fi

log "=== Atomic Extrato CRON Job Completed ==="

# Optional: Send email notification on failure
# Uncomment and configure the following lines if you want email notifications
# if [ $? -ne 0 ]; then
#     echo "Atomic Extrato generation failed. Check logs at $LOG_FILE" | mail -s "Atomic Extrato CRON Error" your-email@example.com
# fi

exit $?

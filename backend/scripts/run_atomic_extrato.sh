#!/bin/bash

# Script to run atomic extrato generation with backup verification
# This ensures backup exists before proceeding with data transfer

# Set the working directory to the backend folder
cd /home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the atomic extrato generation script
echo "Starting atomic extrato generation at $(date)" >> logs/atomic_extrato_cron.log
python scripts/run_atomic_extrato.py >> logs/atomic_extrato_cron.log 2>&1

# Check the exit code
if [ $? -eq 0 ]; then
    echo "Atomic extrato generation completed successfully at $(date)" >> logs/atomic_extrato_cron.log
else
    echo "Atomic extrato generation failed at $(date)" >> logs/atomic_extrato_cron.log
fi

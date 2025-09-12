#!/bin/bash

# Script to run the backup creation process
# This should be called by CRON or manually

# Set the working directory to the backend folder
cd /home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the backup script
echo "Starting backup process at $(date)" >> logs/backup_cron.log
python scripts/create_backup.py >> logs/backup_cron.log 2>&1

# Check the exit code
if [ $? -eq 0 ]; then
    echo "Backup completed successfully at $(date)" >> logs/backup_cron.log
else
    echo "Backup failed at $(date)" >> logs/backup_cron.log
fi</content>
<parameter name="filePath">/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend/scripts/run_backup.sh

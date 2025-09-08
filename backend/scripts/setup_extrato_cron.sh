#!/bin/bash
# Setup cron job for monthly extrato generation
# This should be run as root or with sudo on the production server

# Path to the trigger script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRIGGER_SCRIPT="$SCRIPT_DIR/trigger_extrato.py"

# Create a simple wrapper script
cat > /usr/local/bin/run_monthly_extrato << EOF
#!/bin/bash
# Monthly Extrato Generation Script
cd $SCRIPT_DIR/../..
source venv/bin/activate
python backend/scripts/trigger_extrato.py
EOF

# Make executable and add to crontab
chmod +x /usr/local/bin/run_monthly_extrato
(crontab -l ; echo "0 2 2 * * /usr/local/bin/run_monthly_extrato") | crontab -

echo "✅ Monthly extrato cron job has been set up!"
echo "Will run automatically on the 2nd of each month at 2:00 AM"

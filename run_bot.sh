#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
while true; do
    python -m leaguebot.bot
    echo "Bot exited (code $?). Restarting in 5 seconds..."
    sleep 5
done
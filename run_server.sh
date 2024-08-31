#!/bin/bash

# Activate the virtual environment
source /store/env/bin/activate

while true; do
    python /store/droptracker/disc/main.py
    echo "DropTracker system has crashed. Restarting in ..."
    sleep 5
done


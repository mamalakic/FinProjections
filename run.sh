#!/bin/bash

echo "Starting Budget Tracker..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""

# Run the application
echo "Starting Flask application..."
echo ""
echo "Budget Tracker will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python app.py



#!/bin/bash

echo "Starting Discord Bot..."
echo

# Check if Python is installed and determine command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Python is not installed. Please install Python."
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt

# Start the bot
echo "Starting the bot..."
echo "The invite link will be shown after the bot has started."
echo

$PYTHON_CMD main_ssl_debug.py 
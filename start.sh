#!/bin/bash

# TeamSync Backend Startup Script

echo "======================================"
echo "TeamSync Backend Startup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check database
if [ "$1" == "init" ]; then
    echo "Initializing database..."
    python init_db.py
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Start services
echo ""
echo "Starting services..."
echo "======================================"

# Start Django development server
echo "Starting Django server on http://127.0.0.1:8000"
python manage.py runserver &
DJANGO_PID=$!

# Start Celery worker (if redis is available)
if command -v redis-cli &> /dev/null; then
    echo "Starting Celery worker..."
    celery -A config worker -l info &
    CELERY_PID=$!
fi

echo ""
echo "======================================"
echo "Services started!"
echo "Django: http://127.0.0.1:8000"
echo "Admin: http://127.0.0.1:8000/admin/"
echo "======================================"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for interrupt
trap "kill $DJANGO_PID $CELERY_PID 2>/dev/null; exit" INT
wait

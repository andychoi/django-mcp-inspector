#!/bin/bash

# Activate virtual environment if exists
if [ -d "venv" ]; then
  echo "Activating virtual environment..."
  source venv/bin/activate
fi

# Set Django settings module if not already set
export DJANGO_SETTINGS_MODULE=djproject.settings

# Run migrations (optional: remove if already applied)
echo "Applying Django migrations..."
python manage.py migrate

# Collect static files (optional: only needed for prod)
# echo "Collecting static files..."
# python manage.py collectstatic --noinput

# Create demo superuser if not exists
echo "Creating demo superuser (username: demo)..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='demo').exists():
    User.objects.create_superuser('demo', 'demo@example.com', 'demo')
    print("✔ Created demo superuser")
else:
    print("✔ Demo superuser already exists")
EOF

# Start the server with Uvicorn
echo "Starting Django with Uvicorn..."
uvicorn djproject.asgi:application --host 127.0.0.1 --port 8000 --reload

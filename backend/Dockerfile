FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 300 -r requirements.txt

# Copy project
COPY . .

# Create media, staticfiles, and chroma_db directories
RUN mkdir -p media staticfiles chroma_db

# Run migrations and collect static (ignore errors for fresh setup)
RUN python manage.py migrate --noinput || true
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Run server with gunicorn
CMD ["gunicorn", "rag_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
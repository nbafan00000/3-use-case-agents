# Use a slim Python base image for smaller size (best for production)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first (optimizes caching for faster rebuilds)
COPY requirements.txt .

# Install dependencies (use --no-cache-dir to keep image small)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose the Flask port
EXPOSE 5000

# Set environment variables (Flask defaults; override if needed)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_DEBUG=0

# Run the app (use gunicorn for prod, but flask run is fine for beginner/dev)
CMD ["flask", "run"]
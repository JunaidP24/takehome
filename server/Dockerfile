# Backend Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Clean install
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set Flask environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"] 
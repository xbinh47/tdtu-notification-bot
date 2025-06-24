# Use Python 3.12 slim base image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for Playwright Firefox
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Firefox browser
RUN playwright install firefox
RUN playwright install-deps firefox

# Copy application files
COPY app.py .
COPY scheduler.py .
COPY readed_noti_category_11.txt .
COPY .env* ./

# Create output directory
RUN mkdir -p output

# Run the scheduler (checks every 1 minute)
CMD ["python", "scheduler.py"] 
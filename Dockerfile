# Use Python 3.12 slim base image
FROM python:3.12-slim

WORKDIR /app

# Set timezone to UTC+7 (Asia/Ho_Chi_Minh)
ENV TZ=Asia/Ho_Chi_Minh
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies required for Playwright Firefox
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    tzdata \
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

# Run the scheduler (checks daily at 12:00 PM and 6:00 PM UTC+7)
CMD ["python", "scheduler.py"] 
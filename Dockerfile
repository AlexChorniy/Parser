FROM docker.io/library/python:3.12-slim

# Prevent Python from writing .pyc files and enable live terminal output buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system utilities, base rendering font files, and native Chromium + WebDriver packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set internal operational workspace container directory
WORKDIR /app

# Copy dependency mappings first to utilize system build layer caches
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code into the file architecture layers
COPY . .

# Initialize the script
CMD ["python", "parser.py"]
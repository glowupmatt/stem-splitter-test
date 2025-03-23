FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install all Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project including demucs code
COPY . .

# Create necessary directories with absolute paths
RUN mkdir -p /app/uploads
RUN mkdir -p /root/Downloads/OTGU_Splitter

# Set permissions for the output directory
RUN chmod 777 /root/Downloads/OTGU_Splitter

# Add the project root to PYTHONPATH
ENV PYTHONPATH=/app:/app/server:$PYTHONPATH

# Add the project root to PYTHONPATH
ENV PYTHONPATH=/app:$PYTHONPATH

EXPOSE 8000

WORKDIR /app/server
CMD ["python", "-u", "main.py"]
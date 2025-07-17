FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the universal execution service code
COPY src/sandbox/ src/sandbox/
COPY src/common/ src/common/
COPY docker-entrypoint.sh .

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Set the service name
ENV SERVICE_NAME=universal-execution

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["universal-execution"]
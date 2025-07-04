FROM python:3.9-slim-buster

WORKDIR /app

# Install only basic requirements for file operations
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy sidecar script from the correct path
COPY sidecar/DataSidecar.py .

# Create directories for volumes
RUN mkdir -p /source-data /shared-data

# Set permissions
RUN chmod +x DataSidecar.py

# Run as non-root user
RUN useradd -m -u 1000 sidecar
USER sidecar

CMD ["python", "DataSidecar.py"] 
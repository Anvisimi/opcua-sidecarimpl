FROM python:3.9-slim-buster

WORKDIR /app

# Install git and basic requirements for file operations
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy git-enhanced sidecar script (building from sidecar directory)
COPY DataSidecar.py .

# Run as non-root user (create user first)
RUN useradd -m -u 1000 sidecar

# Create directories for volumes and ensure sidecar user owns them
RUN mkdir -p /data /shared-data /home/sidecar/git-data-repo && \
    chown -R sidecar:sidecar /data /shared-data /home/sidecar/git-data-repo /app

# Set permissions
RUN chmod +x DataSidecar.py

USER sidecar

CMD ["python", "DataSidecar.py"] 
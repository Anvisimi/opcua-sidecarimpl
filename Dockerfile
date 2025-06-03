FROM python:3.9-slim-buster

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y gcc

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY sensor_data.csv .
COPY BoschDataServer.py .
COPY ./data/M01/OP00/good/M01_Aug_2019_OP00_000.h5 .

EXPOSE 4840

CMD ["python", "BoschDataServer.py"]
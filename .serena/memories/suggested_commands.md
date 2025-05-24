# Suggested Shell Commands for OPC UA Server Project

## Development Commands
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server directly
python server.py
```

## Docker Commands
```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Stop the container
docker-compose down

# View logs
docker-compose logs -f
```

## Testing and Validation
```bash
# Check if CSV file exists and is readable
head -5 sensor_data.csv

# Test Python imports
python -c "import asyncua, pandas; print('Dependencies OK')"
```

## System Commands (macOS/Darwin)
```bash
# Common file operations
ls -la
find . -name "*.py"
grep -r "pattern" .
cat filename
head -n 10 filename
tail -f filename

# Process management
ps aux | grep python
kill -9 <pid>
lsof -i :4840  # Check if port is in use
```

## Git Commands
```bash
git status
git add .
git commit -m "message"
git push origin main
```
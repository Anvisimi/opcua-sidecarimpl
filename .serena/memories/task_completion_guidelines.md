# Task Completion Guidelines

## When Development Task is Completed

### 1. Code Quality Checks
Currently no automated linting/formatting is configured. Consider adding:
- Add type hints to function signatures
- Add docstrings to functions
- Add proper logging instead of print statements
- Add error handling and validation

### 2. Testing
No automated testing is currently set up. After adding test cases:
- Run test suite with pytest
- Check test coverage
- Ensure CSV data loading works correctly
- Test OPC UA server connectivity

### 3. Manual Verification
- Run `python server.py` and check for successful startup
- Verify server listens on port 4840
- Test with OPC UA client (like UaExpert)
- Check Docker container builds and runs successfully

### 4. Docker Testing
```bash
docker-compose up --build
# Verify server starts without errors
# Check logs for successful data publishing
docker-compose down
```

### 5. Documentation
- Update README.md if functionality changes
- Document any new configuration options
- Update requirements.txt if new dependencies added

### 6. Version Control
```bash
git add .
git commit -m "Descriptive commit message"
git push origin main
```
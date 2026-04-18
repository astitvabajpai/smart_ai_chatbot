# Testing Guide

Comprehensive testing guide for the Document Chatbot.

## Quick Validation

Run the project validation script:

```bash
python validate_project.py
```

This checks:
- All required modules import correctly
- Configuration loads without errors
- Environment variables are set properly

## Unit Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

## Integration Testing

### Test Locally

1. **Start Services**
   ```bash
   # Terminal 1: API
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Terminal 2: UI
   streamlit run streamlit_app.py
   
   # Terminal 3: Vector DB (if using Qdrant)
   docker run -p 6333:6333 qdrant/qdrant:v1.13.4
   ```

2. **Test Authentication**
   ```bash
   # Register
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "full_name": "Test User",
       "password": "TestPass123"
     }'
   
   # Save the token from response
   TOKEN="<access_token_from_response>"
   
   # Login
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "TestPass123"
     }'
   ```

3. **Test Document Upload**
   ```bash
   # Upload sample PDF
   curl -X POST http://localhost:8000/api/documents/upload \
     -H "Authorization: Bearer $TOKEN" \
     -F "files=@sample.pdf"
   
   # Save job_id from response
   JOB_ID="<job_id_from_response>"
   ```

4. **Test Job Status**
   ```bash
   # Check ingestion progress
   curl -X GET http://localhost:8000/api/jobs/$JOB_ID \
     -H "Authorization: Bearer $TOKEN"
   
   # List all jobs
   curl -X GET http://localhost:8000/api/jobs \
     -H "Authorization: Bearer $TOKEN"
   ```

5. **Test Chat**
   ```bash
   # Synchronous chat
   curl -X POST http://localhost:8000/api/chat \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is in the document?",
       "top_k": 5
     }'
   
   # Streaming chat
   curl -X POST http://localhost:8000/api/chat/stream \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is in the document?",
       "top_k": 5
     }' \
     | grep -o '"data":"[^"]*"'
   ```

6. **Test RAG Evaluation**
   ```bash
   curl -X POST http://localhost:8000/api/rag/evaluate \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is in the document?",
       "expected_answer": "The document discusses...",
       "top_k": 5
     }'
   ```

7. **Test Health Check**
   ```bash
   curl http://localhost:8000/api/health
   ```

## Load Testing

### Using Apache Bench (ab)

```bash
# Test health endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8000/api/health

# Test chat endpoint with load
ab -n 50 -c 5 \
  -H "Authorization: Bearer $TOKEN" \
  -p chat_payload.json \
  http://localhost:8000/api/chat
```

### Using wrk

```bash
# Install wrk
# macOS: brew install wrk
# Ubuntu: sudo apt install wrk
# Windows: Download from https://github.com/wg/wrk

# Basic load test
wrk -t12 -c400 -d30s --latency http://localhost:8000/api/health

# With script
wrk -t12 -c400 -d30s -s test_script.lua --latency http://localhost:8000/api/chat
```

Create `test_script.lua`:
```lua
wrk.method = "POST"
wrk.body = '{"question": "Test question?", "top_k": 5}'
wrk.headers["Authorization"] = "Bearer " .. os.getenv("TOKEN")
wrk.headers["Content-Type"] = "application/json"

function response(status, headers, body)
  if status ~= 200 then
    print("Error: " .. status)
  end
end
```

## Security Testing

### Input Validation

```bash
# Test invalid email
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "invalid-email",
    "full_name": "Test",
    "password": "Pass123"
  }'
# Expected: 400 Bad Request

# Test weak password
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test",
    "password": "weak"
  }'
# Expected: 400 Bad Request

# Test oversized file
dd if=/dev/zero of=large_file.bin bs=1M count=100
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@large_file.bin"
# Expected: 413 Payload Too Large (if > 50MB limit)
```

### Rate Limiting

```bash
# Send rapid requests to trigger rate limit
for i in {1..150}; do
  curl -s http://localhost:8000/api/health > /dev/null
  if [ $((i % 50)) -eq 0 ]; then
    echo "Sent $i requests"
  fi
done

# Should see 429 Too Many Requests after limit
```

### Authentication Testing

```bash
# Test missing token
curl -X GET http://localhost:8000/api/jobs
# Expected: 401 Unauthorized

# Test expired/invalid token
curl -X GET http://localhost:8000/api/jobs \
  -H "Authorization: Bearer invalid_token"
# Expected: 401 Unauthorized

# Test accessing other user's resources
# Create two users, get both tokens
# Try accessing user1's jobs with user2's token
# Expected: 404 Not Found (permission denied)
```

## Performance Testing

### Measure Response Times

```bash
# Using curl with timing
curl -w "@curl_format.txt" -o /dev/null -s \
  http://localhost:8000/api/health
```

Create `curl_format.txt`:
```
    time_namelookup:  %{time_namelookup}\n
       time_connect:  %{time_connect}\n
    time_appconnect:  %{time_appconnect}\n
   time_pretransfer:  %{time_pretransfer}\n
time_redirect:  %{time_redirect}\n
time_starttransfer:  %{time_starttransfer}\n
                  ----------\n
        time_total:  %{time_total}\n
```

### Profile Code

```bash
# Install cProfile
pip install cProfile

# Profile API startup
python -m cProfile -o profile_output.prof -m uvicorn app.main:app

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile_output.prof'); p.sort_stats('cumulative').print_stats(20)"
```

## Error Scenario Testing

### Network Issues

```bash
# Simulate network latency
# macOS/Linux: use tc (traffic control)
sudo tc qdisc add dev lo root netem delay 100ms

# Test API
curl http://localhost:8000/api/health

# Remove simulation
sudo tc qdisc del dev lo root
```

### Database Down

```bash
# Rename database to simulate corruption
mv storage/users.db storage/users.db.bak

# Try to login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Pass123"}'
# Expected: 500 Internal Server Error or auto-recovery

# Restore database
mv storage/users.db.bak storage/users.db
```

### Vector Store Down

```bash
# Stop Qdrant if using it
docker stop <container_id>

# Try to chat
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test?"}'
# Expected: 503 Service Unavailable or 500 error with clear message

# Restart
docker start <container_id>
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      qdrant:
        image: qdrant/qdrant:v1.13.4
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Validate project
        run: python validate_project.py
      
      - name: Run tests
        run: pytest tests/ -v --tb=short
      
      - name: Run linting
        run: |
          pip install pylint
          pylint app/ --fail-under=8.0 || true
```

## Checklist Template

- [ ] All modules import successfully
- [ ] Configuration loads correctly
- [ ] Health check responds
- [ ] Registration works with valid input
- [ ] Registration rejects invalid input
- [ ] Login works with correct credentials
- [ ] Login fails with wrong credentials
- [ ] Only authenticated users can access protected endpoints
- [ ] Document upload works with PDF files
- [ ] Document upload rejects non-PDF files
- [ ] Ingestion job completes successfully
- [ ] Chat generates responses
- [ ] Chat streaming works
- [ ] RAG evaluation metrics are calculated
- [ ] Rate limiting blocks excessive requests
- [ ] Error messages are clear and not exposing internals
- [ ] Logging records all important events
- [ ] Database persists data across restarts
- [ ] Vector store has documents indexed
- [ ] CORS headers are set correctly

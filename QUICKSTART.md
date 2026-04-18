# Quick Start Guide

Get the Document Chatbot up and running in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- Docker (optional, for containerized setup)

## Option 1: Local Development (Fastest)

### 1. Setup

```bash
# Clone and navigate to project
cd smart_ai_chatbot

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add:
# GROQ_API_KEY=your_groq_key_here
# (Optional: OPENAI_API_KEY if using OpenAI embeddings)
```

### 3. Start

```bash
# Terminal 1: API Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Web UI
streamlit run streamlit_app.py

# Terminal 3 (optional): Vector DB - Only if using Qdrant
docker run -p 6333:6333 qdrant/qdrant:v1.13.4
```

### 4. Access

- **UI**: http://localhost:8501
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs

## Option 2: Docker (Recommended for Production)

```bash
# Start all services with Docker Compose
docker compose up --build

# Services:
# - API: http://localhost:8000
# - UI: http://localhost:8501
# - Qdrant: http://localhost:6333
```

Access UI at http://localhost:8501

## First Time Setup

### 1. Register User

In the Streamlit UI:
1. Click "Register" in the auth sidebar
2. Enter email, name, and password (8+ chars, with uppercase, lowercase, number)
3. Click "Submit Auth"

### 2. Upload PDF

1. Upload one or more PDF files using the file uploader
2. Click "Index PDFs"
3. Wait for "Indexed X chunks" confirmation

### 3. Ask Questions

1. In the chat box, ask a question about your documents
2. Watch the AI respond with sources
3. Click "Sources" expander to see retrieved document chunks

## Common Tasks

### Check API Health

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "app_name": "Document Chatbot",
  "embedding_provider": "huggingface",
  "vector_backend": "chroma"
}
```

### Test with cURL

```bash
# 1. Register
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "TestPass123"
  }')

TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 2. Upload PDF (requires actual PDF file)
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@sample.pdf")

JOB_ID=$(echo $JOB_RESPONSE | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

# 3. Check job status
curl -X GET http://localhost:8000/api/jobs/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"

# 4. Chat with documents
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the document about?", "top_k": 5}'
```

## Troubleshooting

### ModuleNotFoundError

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: 
- Make sure you're in the project root directory
- Virtual environment is activated
- Dependencies installed: `pip install -r requirements.txt`

### API Port Already in Use

**Problem**: `Address already in use: ('0.0.0.0', 8000)`

**Solution**:
```bash
# Use different port
uvicorn app.main:app --port 8001

# Or find and kill existing process (Linux/macOS)
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### "No modules named 'GROQ_API_KEY'"

**Problem**: API runs but chat fails with API key error

**Solution**:
1. Create `.env` file: `cp .env.example .env`
2. Add your API keys to `.env`
3. Restart the API server

### Streamlit Cannot Connect to API

**Problem**: "ConnectionError: Failed to establish connection"

**Solution**:
1. Ensure API is running: `curl http://localhost:8000/api/health`
2. Check `API_BASE_URL` in Streamlit sidebar (should be http://localhost:8000/api)
3. No firewall blocking localhost:8000

### Vector Store Connection Error

**Problem**: "Error connecting to Qdrant"

**Solution**:
- If using Qdrant: `docker run -p 6333:6333 qdrant/qdrant:v1.13.4`
- Check `VECTOR_BACKEND` in `.env` matches (should be "qdrant")
- Verify `QDRANT_URL=http://localhost:6333`

## Project Structure

```
smart_ai_chatbot/
├── app/
│   ├── main.py                      # FastAPI app initialization
│   ├── api/
│   │   └── routes.py               # API endpoints
│   ├── core/
│   │   ├── config.py               # Configuration management
│   │   ├── security.py             # JWT and password handling
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── middleware.py           # Error, logging, rate limiting
│   │   ├── validators.py           # Input validation
│   │   ├── logging.py              # Structured logging
│   │   └── rate_limiter.py        # Rate limiting
│   ├── models/
│   │   └── schemas.py              # Pydantic models
│   └── services/
│       ├── chat_service.py         # RAG chat logic
│       ├── document_loader.py      # PDF processing
│       ├── embeddings.py           # Embedding selection
│       ├── retriever.py            # Hybrid retrieval
│       ├── vector_store.py         # Vector DB abstraction
│       ├── job_manager.py          # Async jobs
│       └── user_store.py           # User management
├── streamlit_app.py                # Web UI
├── docker-compose.yml              # Multi-container setup
├── requirements.txt                # Python dependencies
├── .env.example                    # Configuration template
├── README.md                       # This file
├── PRODUCTION_GUIDE.md             # Deployment guide
├── API_DOCUMENTATION.md            # API reference
├── TESTING_GUIDE.md               # Testing procedures
├── CHANGELOG.md                    # Version history
└── validate_project.py             # Project validation
```

## Next Steps

- 📚 Read [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) for deployment
- 📖 See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API details
- 🧪 Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing
- ⚙️ Configure in `.env.example` for your needs

## Support & Help

- Run `python validate_project.py` to check setup
- Check logs: `logs/app.log` and `logs/error.log`
- Test health: `curl http://localhost:8000/api/health`
- API docs: http://localhost:8000/docs (interactive Swagger UI)

## Tips

1. **HuggingFace Embeddings** (default): Fast, works offline after first run
2. **OpenAI Embeddings**: Better quality, but requires API key
3. **Streamlit Rerun**: Hit "R" key to refresh UI if needed
4. **Chat Memory**: Chat history is in session state, lost on refresh
5. **Document Limits**: Each PDF can have multiple chunks processed in background

Enjoy using the Document Chatbot! 🚀

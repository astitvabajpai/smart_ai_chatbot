# API Documentation

Production-ready Document Chatbot API with RAG (Retrieval-Augmented Generation).

## Base URL

```
http://api-server:8000/api
```

## Authentication

All endpoints (except `/health`) require a Bearer token in the `Authorization` header:

```bash
Authorization: Bearer <token>
```

Obtain tokens via `/auth/login` or `/auth/register`.

## Endpoints

### Health & Status

#### GET `/health`

Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "ok",
  "app_name": "Document Chatbot",
  "embedding_provider": "huggingface",
  "groq_model": "llama-3.3-70b-versatile",
  "vector_backend": "chroma"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### Authentication

#### POST `/auth/register`

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

**Status Codes:**
- `200 OK` - User created
- `400 Bad Request` - Invalid input or email already exists
- `500 Internal Server Error` - Server error

**Validation Rules:**
- Email: Valid format, max 254 chars
- Full Name: 2-100 chars, letters/spaces/hyphens/apostrophes only
- Password: Min 8 chars, must include uppercase, lowercase, digit

---

#### POST `/auth/login`

Authenticate user and get token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response:** (Same as register)

**Status Codes:**
- `200 OK` - Login successful
- `400 Bad Request` - Invalid email format
- `401 Unauthorized` - Invalid credentials
- `500 Internal Server Error` - Server error

---

#### GET `/auth/me`

Get current authenticated user info.

**Response:**
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe"
}
```

**Status Codes:**
- `200 OK` - User info retrieved
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Server error

---

### Documents

#### POST `/documents/upload`

Upload PDF documents for ingestion.

**Request:** (multipart/form-data)
- `files`: PDF files to upload (multiple allowed)

**Response:**
```json
{
  "status": "queued",
  "files": ["document1.pdf", "document2.pdf"],
  "chunks_indexed": 0,
  "job_id": "job-uuid-here"
}
```

**Status Codes:**
- `200 OK` - Files queued for ingestion
- `400 Bad Request` - Invalid files or no files provided
- `401 Unauthorized` - Invalid token
- `413 Payload Too Large` - File exceeds max size
- `500 Internal Server Error` - Server error

**Validation:**
- Only PDF files allowed
- Max file size: 50MB (configurable)
- Max total request size: 100MB

---

#### GET `/jobs`

List all ingestion jobs for current user.

**Response:**
```json
[
  {
    "job_id": "job-uuid",
    "user_id": "user-uuid",
    "job_type": "ingestion",
    "status": "completed",
    "result": {
      "files": ["doc1.pdf"],
      "chunks_indexed": 42
    },
    "error": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
  }
]
```

**Status:** `queued`, `running`, `completed`, or `failed`

**Status Codes:**
- `200 OK` - Jobs retrieved
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Server error

---

#### GET `/jobs/{job_id}`

Get specific job status.

**Response:** (Single job object, same structure as above)

**Status Codes:**
- `200 OK` - Job retrieved
- `401 Unauthorized` - Invalid token
- `404 Not Found` - Job not found
- `500 Internal Server Error` - Server error

---

### Chat

#### POST `/chat`

Generate answer from documents (synchronous, waits for full response).

**Request:**
```json
{
  "question": "What is machine learning?",
  "chat_history": [
    {
      "role": "user",
      "content": "Previous question"
    },
    {
      "role": "assistant",
      "content": "Previous answer"
    }
  ],
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Machine learning is a subset of artificial intelligence...",
  "rewritten_query": "what is machine learning definition",
  "query_variants": [
    "machine learning definition",
    "what defines machine learning",
    "machine learning explained"
  ],
  "sources": [
    {
      "document_id": "doc-hash",
      "file_name": "ml-guide.pdf",
      "page": 5,
      "chunk_id": "doc-hash-chunk-0",
      "excerpt": "Machine learning is... [first 300 chars]"
    }
  ],
  "retrieval_debug": {
    "strategy": "hybrid",
    "dense_hits": 25,
    "lexical_hits": 18,
    "query_count": 3
  }
}
```

**Status Codes:**
- `200 OK` - Answer generated
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Server error

**Validation:**
- Question: 3-5000 chars
- top_k: 1-50 (default: 5)
- Chat history: Valid JSON array

---

#### POST `/chat/stream`

Generate answer with Server-Sent Events (SSE) streaming.

**Response:** EventStream (text/event-stream)

Events emitted:
```
event: meta
data: {"rewritten_query": "...", "query_variants": [...], "sources": [...], "retrieval_debug": {...}}

event: token
data: "partial response text"

event: token
data: " continues..."

event: done
data: "completed"
```

**Status Codes:**
- `200 OK` - Stream started
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Server error

---

### RAG Evaluation

#### POST `/rag/evaluate`

Evaluate RAG system quality with metrics.

**Request:**
```json
{
  "question": "What is machine learning?",
  "expected_answer": "ML is a type of AI where systems learn from data",
  "chat_history": [],
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Machine learning is...",
  "rewritten_query": "...",
  "query_variants": [...],
  "metrics": {
    "answer_similarity": 0.87,
    "context_precision": 0.92,
    "retrieved_sources": 3.0
  },
  "sources": [...],
  "retrieval_debug": {...}
}
```

**Metrics:**
- `answer_similarity` (0-1): How similar generated answer is to expected
- `context_precision` (0-1): How grounded answer is in sources
- `retrieved_sources` (int): Number of sources used

**Status Codes:**
- `200 OK` - Evaluation complete
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Server error

---

## Error Handling

All errors return standardized JSON:

```json
{
  "error": "Error message here",
  "details": {
    "field": "validation detail"
  }
}
```

**Common HTTP Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found (resource doesn't exist) |
| 409 | Conflict (email already registered) |
| 413 | Payload Too Large (file too big) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Rate Limiting

Default: 100 requests per 60 seconds per IP address.

Responses will include rate limit info in headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

When limit exceeded: `429 Too Many Requests`

---

## Request/Response Format

- **Content-Type**: `application/json` (except file uploads)
- **Charset**: UTF-8
- **Max Body Size**: 10MB (configurable, default 50MB for uploads)
- **Request Timeout**: 120 seconds (default, configurable)

---

## Examples

### Example: Complete Chat Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "SecurePass123"
  }'

# Response: { "access_token": "...", "user": {...} }

# 2. Upload documents
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf"

# Response: { "job_id": "...", "status": "queued", ... }

# 3. Check job status
curl -X GET http://localhost:8000/api/jobs/<job_id> \
  -H "Authorization: Bearer <token>"

# Response: { "status": "completed", "result": {...} }

# 4. Chat with documents
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What does the document say?",
    "top_k": 5
  }'

# Response: { "answer": "...", "sources": [...] }
```

---

## WebSocket Support

Not currently implemented. Use SSE (`/chat/stream`) for streaming.

---

## API Changelog

### v1.0.0 (Current)
- Initial production release
- Authentication with JWT
- Multi-backend vector store support
- Streaming chat responses
- RAG evaluation metrics
- Rate limiting
- Comprehensive error handling

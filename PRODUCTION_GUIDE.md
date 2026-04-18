# Production Deployment Guide

This guide covers deploying the Document Chatbot to a production environment.

## Pre-Deployment Checklist

- [ ] Set all environment variables in `.env` (copy from `.env.example`)
- [ ] Change `JWT_SECRET_KEY` to a strong random value (min 32 characters)
- [ ] Set `APP_ENV=production`
- [ ] Configure `GROQ_API_KEY` and embedding provider keys
- [ ] Ensure vector database is configured (Chroma, Pinecone, or Qdrant)
- [ ] Review and update CORS origins for your domain
- [ ] Set up SSL/TLS certificates
- [ ] Configure database backups
- [ ] Enable rate limiting
- [ ] Set up monitoring and logging
- [ ] Test everything in staging first

## Environment Configuration

### Critical Production Settings

```bash
# Application
APP_ENV=production
API_WORKERS=4  # Increase based on CPU cores
JWT_SECRET_KEY=your-very-long-random-secret-key-here-at-least-32-chars
JWT_EXPIRE_MINUTES=60

# Security
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
MAX_UPLOAD_SIZE_MB=50
PASSWORD_MIN_LENGTH=8

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD_SECONDS=60

# AI Services
GROQ_API_KEY=your-groq-key
EMBEDDING_PROVIDER=huggingface  # or openai
VECTOR_BACKEND=chroma  # or pinecone, qdrant

# Logging
LOG_LEVEL=INFO
```

## Docker Deployment

### Build and Run with Docker Compose

```bash
# Build images
docker compose -f docker-compose.yml build

# Start services
docker compose -f docker-compose.yml up -d

# View logs
docker compose logs -f api
docker compose logs -f ui

# Stop services
docker compose down
```

### Kubernetes Deployment

Create a `k8s-deployment.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: document-chatbot

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: document-chatbot
data:
  APP_ENV: "production"
  LOG_LEVEL: "INFO"
  VECTOR_BACKEND: "qdrant"
  QDRANT_URL: "http://qdrant:6333"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-api
  namespace: document-chatbot
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: chatbot-api
  template:
    metadata:
      labels:
        app: chatbot-api
    spec:
      containers:
      - name: api
        image: chatbot-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: app-config
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: jwt-secret
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: groq-api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: storage
          mountPath: /app/storage
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: chatbot-storage

---
apiVersion: v1
kind: Service
metadata:
  name: chatbot-api
  namespace: document-chatbot
spec:
  type: LoadBalancer
  selector:
    app: chatbot-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

Deploy with:
```bash
kubectl create secret generic app-secrets \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  --from-literal=groq-api-key=$GROQ_API_KEY \
  -n document-chatbot

kubectl apply -f k8s-deployment.yaml
```

## Running Locally for Development

### Setup

```bash
# Create virtual environment
python -m venv venv

# Activate venv
# On Windows:
venv\Scripts\activate
# On Unix:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your API keys
```

### Start Services

```bash
# Terminal 1: API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit UI
streamlit run streamlit_app.py

# Terminal 3: Qdrant (if using vector backend)
docker run -p 6333:6333 qdrant/qdrant:v1.13.4
```

Access UI at: `http://localhost:8501`

## Monitoring & Logging

### Check Application Health

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "ok",
  "app_name": "Document Chatbot",
  "embedding_provider": "huggingface",
  "groq_model": "llama-3.3-70b-versatile",
  "vector_backend": "chroma"
}
```

### View Logs

Logs are written to `logs/app.log` and `logs/error.log` with rotation.

```bash
# Follow real-time logs
tail -f logs/app.log

# Check error logs
cat logs/error.log
```

### Monitor in Production

Set up monitoring for:
- API response times
- Error rates
- Rate limit violations
- Document ingestion job failures
- Vector store health
- Database connectivity

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Documents

- `POST /api/documents/upload` - Upload PDFs
- `GET /api/jobs` - List ingestion jobs
- `GET /api/jobs/{job_id}` - Get job status

### Chat

- `POST /api/chat` - Chat synchronously
- `POST /api/chat/stream` - Chat with streaming
- `POST /api/rag/evaluate` - Evaluate RAG quality

### System

- `GET /api/health` - Health check

## Security Best Practices

1. **Enable HTTPS/TLS** in production
2. **Use strong JWT secret**: Generate with `openssl rand -base64 32`
3. **Restrict CORS origins** - don't use `*`
4. **Enable rate limiting** - prevent abuse
5. **Set max upload size** - prevent DoS attacks
6. **Validate all inputs** - already implemented
7. **Use environment variables** - never commit secrets
8. **Monitor access logs** - detect suspicious activity
9. **Keep dependencies updated** - run `pip install --upgrade -r requirements.txt`
10. **Run behind a reverse proxy** - use Nginx or similar

## Performance Tuning

### API Workers

```bash
# Default: 2 workers
# Production: CPU cores * 2 to 4
API_WORKERS=8

# In docker-compose.yml or kubernetes, update deployment
```

### Rate Limiting

Adjust based on your needs:
```bash
RATE_LIMIT_REQUESTS=100        # requests
RATE_LIMIT_PERIOD_SECONDS=60   # per minute
```

### Database Optimization

For SQLite (default):
- Good for <1000 concurrent users
- For larger, use PostgreSQL

For Vector DB:
- Chroma: local, for development/small scale
- Qdrant: self-hosted, production-ready
- Pinecone: fully managed, recommended for scale

### Request Timeouts

```bash
REQUEST_TIMEOUT_SECONDS=120    # general requests
UPLOAD_TIMEOUT_SECONDS=300     # long document processing
```

## Backup & Recovery

### Database Backup

```bash
# SQLite backup
cp storage/users.db storage/users.db.backup

# Scheduled backup (cron)
0 2 * * * cp /path/to/storage/users.db /backups/users.db.$(date +\%Y\%m\%d)
```

### Vector Store Backup

- **Chroma**: Backup `storage/chroma` directory
- **Qdrant**: Built-in snapshots via API
- **Pinecone**: Managed by provider

## Troubleshooting

### API won't start

```bash
# Check logs
docker logs chatbot-api

# Verify environment variables
echo $GROQ_API_KEY

# Test configuration
python -c "from app.core.config import get_settings; print(get_settings())"
```

### High memory usage

- Reduce `API_WORKERS`
- Check for long-running jobs
- Monitor vector store size

### Slow document ingestion

- Check disk I/O
- Verify embedding dimensions match
- Monitor CPU usage during chunking

### Chat responses are slow

- Check RAG retrieval time
- Verify vector store is healthy
- Monitor network latency to embedding service

## Updates & Maintenance

### Rolling Updates with Docker Compose

```bash
# Update image while keeping data
docker compose pull
docker compose up -d --no-deps --build api
docker compose up -d --no-deps --build ui
```

### Database Schema Updates

Before upgrading:
1. Backup databases
2. Test in staging
3. Plan downtime if needed
4. Have rollback plan

## Support & Resources

- **Documentation**: See `README.md`
- **Issue Tracking**: Create GitHub issues
- **Logs**: Check `logs/app.log` and `logs/error.log`
- **Health Check**: `GET /api/health`

## Production Checklist Template

```yaml
Pre-Launch:
  - [ ] All environment variables configured
  - [ ] SSL/TLS certificates in place
  - [ ] Database backups automated
  - [ ] Rate limiting tested
  - [ ] Staging deployment successful
  - [ ] Security audit completed
  - [ ] Performance tested under load
  - [ ] Monitoring & alerting configured

Launch:
  - [ ] DNS configured
  - [ ] CDN setup (if needed)
  - [ ] Analytics enabled
  - [ ] Logging verified
  - [ ] Support process documented

Post-Launch:
  - [ ] Monitor error rates
  - [ ] Check performance metrics
  - [ ] Gather user feedback
  - [ ] Plan optimization
```

# QAMill Production Deployment Guide

**Phase 7: Production Deployment Complete**

---

## Quick Start

### Option 1: Docker Compose (Development/Staging)

```bash
# Clone repository
git clone https://github.com/yourusername/qamill.git
cd qamill

# Create environment file
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# Access application
# Backend: http://localhost:8765
# Frontend: http://localhost:5173
```

### Option 2: Kubernetes (Production)

```bash
# Create namespace and deploy
kubectl apply -f k8s-deployment.yaml

# Wait for rollout
kubectl rollout status deployment/qamill-api -n qamill

# Check services
kubectl get services -n qamill
```

---

## Prerequisites

### System Requirements
- **CPU:** 2+ cores minimum
- **RAM:** 4GB minimum (8GB recommended)
- **Storage:** 20GB SSD minimum
- **Network:** High-speed connection (100Mbps+)

### Required Services
- **PostgreSQL 13+** - Database
- **Redis 6+** - Caching & sessions
- **Docker** - Container runtime
- **Kubernetes 1.24+** - Orchestration (optional)

### Required Credentials
- GitHub OAuth credentials
- Google OAuth credentials
- Anthropic API key (or alternative LLM)
- AWS credentials (for S3 storage, optional)

---

## Docker Setup

### Build Image

```bash
# Build Docker image
docker build -t qamill:1.2.0 .

# Tag for registry
docker tag qamill:1.2.0 your-registry/qamill:1.2.0

# Push to registry
docker push your-registry/qamill:1.2.0
```

### Run Container

```bash
docker run -d \
  --name qamill-api \
  -p 8765:8765 \
  -e DATABASE_URL="postgresql://user:pass@localhost/qamill" \
  -e AUTH_JWT_SECRET="your-secret-key" \
  -e OAUTH_GITHUB_CLIENT_ID="github-id" \
  -e OAUTH_GITHUB_CLIENT_SECRET="github-secret" \
  your-registry/qamill:1.2.0
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (optional, for package management)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace qamill

# Create secrets
kubectl create secret generic qamill-secrets \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=AUTH_JWT_SECRET="..." \
  -n qamill

# Deploy application
kubectl apply -f k8s-deployment.yaml

# Verify deployment
kubectl get deployments -n qamill
kubectl get pods -n qamill
kubectl get services -n qamill

# View logs
kubectl logs -f deployment/qamill-api -n qamill
```

### Scaling

```bash
# Scale manually
kubectl scale deployment/qamill-api --replicas=5 -n qamill

# Or use HPA (automatic scaling)
kubectl get hpa -n qamill
kubectl describe hpa qamill-api-hpa -n qamill
```

---

## Database Setup

### PostgreSQL Initialization

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres

# Create database
CREATE DATABASE qamill;

# Create user
CREATE USER qamill_user WITH PASSWORD 'secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE qamill TO qamill_user;

# Connect and run migrations
\c qamill
```

### Run Migrations

```bash
# Using Alembic (when implemented in Phase 7)
alembic upgrade head
```

---

## Environment Configuration

### Production Variables

```env
# Required
DATABASE_URL=postgresql://user:password@host:5432/qamill
AUTH_JWT_SECRET=random-secret-key-min-32-chars
OAUTH_GITHUB_CLIENT_ID=your-github-id
OAUTH_GITHUB_CLIENT_SECRET=your-github-secret
OAUTH_GOOGLE_CLIENT_ID=your-google-id
OAUTH_GOOGLE_CLIENT_SECRET=your-google-secret

# Optional but recommended
ENVIRONMENT=production
API_DEBUG=false
STORAGE_TYPE=s3
REDIS_URL=redis://redis:6379
LOG_LEVEL=INFO
```

### OAuth Setup

#### GitHub
1. Go to Settings > Developer settings > OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL: `https://yourdomain.com/auth/github/callback`
4. Copy Client ID and Secret to `.env.production`

#### Google
1. Go to https://console.cloud.google.com/
2. Create new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `https://yourdomain.com/auth/google/callback`
6. Copy credentials to `.env.production`

---

## Security Hardening

### SSL/TLS

```bash
# Using Let's Encrypt with Certbot
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Configure Nginx with SSL
# See nginx.conf.example for configuration
```

### Firewall Setup

```bash
# Allow necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

### Database Security

```bash
# Restrict database access
# Only allow connections from application server

# Create read-only user for reports
CREATE USER qamill_reader WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE qamill TO qamill_reader;
GRANT USAGE ON SCHEMA public TO qamill_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qamill_reader;
```

---

## Monitoring & Logging

### Logging Setup

```bash
# Create log directory
sudo mkdir -p /var/log/qamill
sudo chown nobody:nogroup /var/log/qamill
sudo chmod 755 /var/log/qamill

# Configure log rotation (logrotate)
sudo tee /etc/logrotate.d/qamill > /dev/null <<EOF
/var/log/qamill/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 nobody nogroup
    sharedscripts
    postrotate
        systemctl reload qamill
    endscript
}
EOF
```

### Health Checks

```bash
# Check API health
curl http://localhost:8765/health

# Check WebSocket connection
wscat -c "ws://localhost:8765/ws/project/test?token=YOUR_TOKEN"

# Check database connection
curl http://localhost:8765/api/v1/projects
```

---

## Backup & Recovery

### Database Backups

```bash
# Automated daily backups
0 2 * * * pg_dump -h localhost -U qamill_user qamill | gzip > /backups/qamill-$(date +\%Y\%m\%d).sql.gz

# Restore from backup
gunzip < /backups/qamill-20260627.sql.gz | psql -h localhost -U qamill_user qamill
```

### Application Data Backups

```bash
# Backup storage directory
tar -czf /backups/qamill-storage-$(date +%Y%m%d).tar.gz /var/lib/qamill/storage/

# Backup configuration
tar -czf /backups/qamill-config-$(date +%Y%m%d).tar.gz /etc/qamill/
```

---

## CI/CD Pipeline

### GitHub Actions Setup

1. Create `.github/workflows/deploy.yml`
2. Add repository secrets:
   - `KUBE_CONFIG` - Base64 encoded kubeconfig
   - `SLACK_WEBHOOK` - Slack notification webhook
   - `DOCKER_REGISTRY_TOKEN` - Container registry token

3. On push to main:
   - Run tests
   - Build Docker image
   - Push to registry
   - Deploy to Kubernetes
   - Notify Slack

### Manual Deployment

```bash
# Update code
git pull origin main

# Build image
docker build -t qamill:1.2.0 .

# Push to registry
docker push your-registry/qamill:1.2.0

# Update Kubernetes
kubectl set image deployment/qamill-api \
  qamill-api=your-registry/qamill:1.2.0 \
  -n qamill

# Monitor rollout
kubectl rollout status deployment/qamill-api -n qamill
```

---

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker logs qamill-api

# Check database connection
psql -h localhost -U qamill_user -d qamill -c "SELECT 1"

# Verify environment variables
docker run -it your-registry/qamill:1.2.0 env | sort
```

### Database Connection Issues

```bash
# Test connection
nc -zv database.example.com 5432

# Check PostgreSQL status
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### WebSocket Connection Failed

```bash
# Check Kubernetes service
kubectl get svc -n qamill

# Port forward for testing
kubectl port-forward svc/qamill-api 8765:80 -n qamill

# Test connection
curl http://localhost:8765/health
```

---

## Performance Tuning

### PostgreSQL

```sql
-- Optimize shared buffers (25% of system RAM)
ALTER SYSTEM SET shared_buffers = '4GB';

-- Optimize work memory
ALTER SYSTEM SET work_mem = '16MB';

-- Enable connection pooling (use PgBouncer)
```

### Redis

```bash
# Monitor Redis performance
redis-cli info stats

# Optimize memory
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Application

```bash
# Increase worker count for CPU-bound operations
# In docker-compose.yml or k8s-deployment.yaml
workers: 4  # Default for 2-core system

# Adjust for your system: workers = CPU_cores * 2 + 1
```

---

## Upgrade Path

### Version Upgrade Procedure

```bash
# 1. Backup everything
./scripts/backup.sh

# 2. Build new image
docker build -t qamill:1.3.0 .

# 3. Test in staging
docker-compose -f docker-compose.staging.yml up -d

# 4. Deploy to production
kubectl set image deployment/qamill-api \
  qamill-api=your-registry/qamill:1.3.0 -n qamill

# 5. Monitor rollout
kubectl rollout status deployment/qamill-api -n qamill

# 6. Verify health
curl https://yourdomain.com/health
```

---

## Support & Documentation

### Useful Links
- GitHub Repository: https://github.com/yourusername/qamill
- Documentation: https://docs.qamill.io
- API Docs: https://api.qamill.io/docs
- Status Page: https://status.qamill.io

### Get Help
- Issues: https://github.com/yourusername/qamill/issues
- Discussions: https://github.com/yourusername/qamill/discussions
- Email: support@qamill.io

---

## Checklist Before Launch

- [ ] All environment variables configured
- [ ] Database created and migrations run
- [ ] OAuth credentials set up
- [ ] SSL certificates installed
- [ ] Firewall configured
- [ ] Backups enabled
- [ ] Monitoring set up
- [ ] Load balancer configured
- [ ] CDN configured (optional)
- [ ] Domain DNS updated
- [ ] Health checks passing
- [ ] Performance baseline established

---

**Ready to launch! 🚀**

Deploy with confidence knowing QAMill is production-ready.

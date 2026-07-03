# QAMill Production Deployment Guide

## Overview

This guide ensures the QAMill backend runs reliably in production without fatal errors.

---

## 1. Pre-Deployment Checklist

- [ ] Python 3.10+ installed
- [ ] All dependencies in `requirements.txt` installed
- [ ] `.env.production` configured
- [ ] API keys set in environment variables (not in files)
- [ ] Logs directory exists and is writable
- [ ] Database is set up
- [ ] SSL certificates ready (if using HTTPS)

---

## 2. Installation Setup

### Windows / Local Testing

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Linux Production (Using systemd)

```bash
# 1. Create qamill user
sudo useradd -m -s /bin/bash qamill

# 2. Clone repository
cd /opt && sudo git clone https://github.com/AT-Solves/QAMill.git qamill
cd /opt/qamill

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 4. Create logs directory
mkdir -p backend/logs
sudo chown -R qamill:qamill /opt/qamill

# 5. Install systemd service
sudo cp backend/qamill.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable qamill
sudo systemctl start qamill

# 6. Check status
sudo systemctl status qamill
sudo journalctl -u qamill -f  # Follow logs
```

### Production (Using PM2)

```bash
# 1. Install PM2 globally
npm install -g pm2

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Start with PM2
pm2 start ecosystem.config.js --env production

# 4. Save PM2 process list
pm2 save

# 5. Set up PM2 to start on boot
pm2 startup
pm2 save

# 6. Monitor
pm2 monitor
pm2 logs qamill-backend
```

---

## 3. Health Check Endpoints

The backend provides real-time health monitoring:

### Check Server Health
```bash
curl http://localhost:8765/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-30T10:30:00.000Z",
  "uptime": {
    "seconds": 3600,
    "minutes": 60,
    "hours": 1
  },
  "requests": 150,
  "errors": 2,
  "last_error": null,
  "system": {
    "cpu_percent": 15.2,
    "memory_mb": 256,
    "memory_percent": 25.3,
    "threads": 8
  }
}
```

**Status Meanings:**
- `healthy`: Everything working normally
- `degraded`: High memory or error rate but still running
- `unhealthy`: Critical issues detected

---

## 4. Error Handling

### What Happens on Error

1. **Error Occurs** → Logged with full context
2. **Monitor Records** → Error count incremented
3. **Response Sent** → User gets clear error message
4. **No Crash** → Server keeps running
5. **Auto-Recovery** → systemd/PM2 monitors and restarts if needed

### Example Error Response

```json
{
  "error": true,
  "message": "Internal server error. Please try again later.",
  "type": "ValueError",
  "code": 500
}
```

---

## 5. Logging & Monitoring

### Log Files Location

- **systemd**: `journalctl -u qamill -f`
- **PM2**: `pm2 logs qamill-backend`
- **File**: `backend/logs/qamill.log`

### Monitor Critical Metrics

```bash
# System resources
pm2 monit

# Process status
pm2 status

# Real-time logs
pm2 logs qamill-backend

# Error logs
tail -f backend/logs/qamill.log | grep ERROR
```

### Alerting Setup

Monitor these metrics for alerting:

- **Memory > 90%** → WARNING
- **CPU > 80%** → WARNING
- **Error count > 50** → ALERT
- **Server down > 1 min** → CRITICAL

---

## 6. Automatic Recovery

### systemd Recovery (Linux)

The `qamill.service` file has:

```
Restart=always
RestartSec=10
```

This means:
- ✅ Auto-restarts if process crashes
- ✅ Waits 10 seconds between restarts
- ✅ Prevents restart loops
- ✅ Logs all restarts

### PM2 Recovery

```
max_restarts: 5
min_uptime: '10s'
```

This means:
- ✅ Auto-restarts on crash
- ✅ Max 5 restarts before manual intervention
- ✅ Requires 10+ seconds uptime to count as "good"
- ✅ Prevents infinite restart loops

### Manual Recovery

```bash
# systemd
sudo systemctl restart qamill

# PM2
pm2 restart qamill-backend
pm2 reload qamill-backend  # Zero-downtime reload
```

---

## 7. Port Binding Issues (Common Problem)

### Error:
```
error while attempting to bind on address ('127.0.0.1', 8765):
[winerror 10048] only one usage of each socket address is normally permitted
```

### Solutions:

**Option 1: Kill existing process**
```bash
# Windows
netstat -ano | findstr :8765
taskkill /PID <PID> /F

# Linux
lsof -i :8765
kill -9 <PID>
```

**Option 2: Use different port**
```bash
QAMILL_PORT=9765 python backend/main.py
```

**Option 3: Wait for TIME_WAIT**
```bash
# Port stays in TIME_WAIT for ~2 minutes, just wait
sleep 120
python backend/main.py
```

---

## 8. Environment Variables

### Required (Production)

```bash
export QAMILL_HOST=0.0.0.0
export QAMILL_PORT=8765
export ENVIRONMENT=production
export DEBUG=false
```

### Optional (API Keys - Never commit these!)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export SMTP_PASSWORD=your_password
```

Load from `.env.production`:

```bash
set -a
source backend/.env.production
set +a
```

---

## 9. Monitoring Dashboard

Create a monitoring endpoint to track health:

```bash
# Health API (already built in)
curl http://localhost:8765/health | jq

# Implement custom dashboard
# See health_check.py for integration points
```

---

## 10. Deployment Checklist

### Pre-Deploy
- [ ] All tests pass
- [ ] Code reviewed
- [ ] Dependencies updated
- [ ] Environment variables set
- [ ] Database backups taken
- [ ] Logs rotate configured

### Deploy
- [ ] Stop old instance
- [ ] Pull latest code
- [ ] Install dependencies
- [ ] Run migrations
- [ ] Start new instance
- [ ] Verify health endpoint
- [ ] Verify core functionality

### Post-Deploy
- [ ] Monitor error logs
- [ ] Check resource usage
- [ ] Verify all endpoints work
- [ ] Check response times
- [ ] Alert team if issues

---

## 11. Graceful Shutdown

The server handles graceful shutdown:

```bash
# systemd (30-second timeout)
sudo systemctl stop qamill

# PM2
pm2 stop qamill-backend
pm2 delete qamill-backend  # Remove from PM2

# Direct (SIGTERM)
kill -TERM <PID>
```

---

## 12. Scaling

### Single Server
- Use systemd on Linux
- Use PM2 for easier management
- Monitor with systemd or PM2

### Multiple Servers
- Use load balancer (nginx, HAProxy)
- Run backend on each server
- Centralize logs (ELK Stack, Datadog)
- Use database for sessions

---

## 13. Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Kill process or change port |
| High memory usage | Check for memory leaks, restart |
| High error rate | Check logs, debug specific endpoint |
| Slow performance | Check CPU/Memory, optimize queries |
| Server won't start | Check logs, verify Python/dependencies |
| Not restarting on crash | Check systemd/PM2 config |

---

## 14. Support

- Check logs: `journalctl -u qamill -f` or `pm2 logs`
- Health endpoint: `curl http://localhost:8765/health`
- GitHub Issues: https://github.com/AT-Solves/QAMill/issues
- Documentation: https://github.com/AT-Solves/QAMill/wiki

---

**You're now running QAMill in production with automatic recovery, monitoring, and error handling!** ✨

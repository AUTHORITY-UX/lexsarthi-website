# 🚀 Advocacy & Law Firm - Production Deployment Guide

## Domain: www.advocacyalawfirm.in

Complete deployment instructions for pushing the professional law firm website to production.

---

## 📋 Pre-Deployment Checklist

- [ ] All files created (law-firm.html, frontend_routes.py)
- [ ] Backend routes integrated in app.py
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] SSL certificates prepared
- [ ] DNS records updated
- [ ] Monitoring configured

---

## 🔧 Integration with app.py

Add these lines to **app.py** if not already present:

```python
# At the top, with other imports
from frontend_routes import router as frontend_router

# In your FastAPI app initialization (after app = FastAPI(...))
app.include_router(frontend_router)

# This registers all endpoints:
# - POST /api/v1/consultation
# - POST /api/v1/contact
# - GET /api/v1/services
# - GET /api/v1/info
# - GET /api/v1/consultations/{id}
```

---

## 📦 Deployment Options

### Option 1: Fly.io (Recommended for Speed)

**Prerequisites:**
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login to Fly
flyctl auth login
```

**Deploy:**
```bash
# Create app (one-time)
flyctl apps create advocacy-law-firm

# Set environment variables
flyctl secrets set \
  ENVIRONMENT=production \
  ZERO_DATA_RETENTION=true \
  DOMAIN=www.advocacyalawfirm.in

# Deploy
flyctl deploy

# Get app URL
flyctl open
```

**Configure Domain:**
```bash
# Create SSL certificate
flyctl certs create www.advocacyalawfirm.in

# Update your domain DNS to point to:
# Type: CNAME
# Value: advocacy-law-firm.fly.dev
```

---

### Option 2: Docker + Cloud Run (Google Cloud)

**Build and Push:**
```bash
# Build image
docker build -t gcr.io/YOUR_PROJECT/advocacy-law-firm:latest .

# Push to registry
docker push gcr.io/YOUR_PROJECT/advocacy-law-firm:latest

# Deploy to Cloud Run
gcloud run deploy advocacy-law-firm \
  --image gcr.io/YOUR_PROJECT/advocacy-law-firm:latest \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production
```

---

### Option 3: AWS ECS + ALB

**Create ECR Repository:**
```bash
# Create repository
aws ecr create-repository --repository-name advocacy-law-firm

# Login
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

# Build and push
docker build -t advocacy-law-firm:latest .
docker tag advocacy-law-firm:latest YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/advocacy-law-firm:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/advocacy-law-firm:latest
```

**Deploy with ECS:**
- Create ECS cluster
- Create task definition with ECR image
- Create ECS service
- Attach Application Load Balancer
- Configure Route53 DNS

---

### Option 4: Heroku

**Deploy:**
```bash
# Login
heroku login

# Create app
heroku create advocacy-law-firm

# Set config vars
heroku config:set ENVIRONMENT=production
heroku config:set ZERO_DATA_RETENTION=true

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

**Add Custom Domain:**
```bash
heroku domains:add www.advocacyalawfirm.in
```

Then update DNS with the Heroku nameservers.

---

## 🌐 DNS Configuration

### For Fly.io:
```
Type: CNAME
Name: www
Value: advocacy-law-firm.fly.dev
```

### For Google Cloud Run:
```
Type: A
Value: [Load Balancer IP from Cloud Run]
```

### For AWS:
```
Type: CNAME
Value: [ALB DNS Name]
```

### For Heroku:
```
Type: CNAME
Value: advocacy-law-firm.herokuapp.com
```

---

## 📝 Environment Variables

Create `.env` file with:

```env
# Server
ENVIRONMENT=production
DEBUG=false
PORT=8000

# Domain
DOMAIN=www.advocacyalawfirm.in

# Database (if using)
DATABASE_URL=postgresql://user:pass@host/dbname

# Redis (optional)
REDIS_URL=redis://localhost:6379

# LLM Providers
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...

# Email (for consultations)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
ADMIN_EMAIL=hello@advocacyalawfirm.in

# Features
ZERO_DATA_RETENTION=true
HUMAN_GATED_EVOLUTION=true
ENABLE_MARKETING_DRAFTS=false
```

---

## ✅ Post-Deployment Verification

### 1. Health Check
```bash
curl https://www.advocacyalawfirm.in/health
```

Expected Response:
```json
{"status": "healthy", "timestamp": "2026-09-01T..."}
```

### 2. API Status
```bash
curl https://www.advocacyalawfirm.in/status
```

### 3. Frontend Access
```bash
# Web UI
https://www.advocacyalawfirm.in/static/law-firm.html

# Chat Interface
https://www.advocacyalawfirm.in/chat

# API Docs
https://www.advocacyalawfirm.in/docs
```

### 4. Contact Form Test
```bash
curl -X POST https://www.advocacyalawfirm.in/api/v1/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "message": "Test message"
  }'
```

### 5. Consultation Request Test
```bash
curl -X POST https://www.advocacyalawfirm.in/api/v1/consultation \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Consultant",
    "email": "consultant@example.com",
    "phone": "+91 9876543210",
    "issueType": "Corporate Law",
    "description": "Need legal advice"
  }'
```

---

## 🔒 SSL/TLS Certificate

### Automatic (Fly.io, Cloud Run):
Certificates are automatically managed by the platform.

### Manual (AWS, Custom):
```bash
# Using Let's Encrypt
sudo certbot certonly --standalone -d www.advocacyalawfirm.in

# Upload to your server
```

---

## 📊 Monitoring & Logging

### Fly.io:
```bash
# View logs
flyctl logs -a advocacy-law-firm

# Monitor metrics
flyctl metrics -a advocacy-law-firm

# Check deployments
flyctl releases -a advocacy-law-firm
```

### Google Cloud Run:
```bash
# View logs
gcloud run logs read advocacy-law-firm --platform managed

# Monitor metrics
gcloud monitoring --project=YOUR_PROJECT
```

### AWS CloudWatch:
```bash
# View logs
aws logs tail /ecs/advocacy-law-firm --follow

# Monitor metrics
aws cloudwatch get-metric-statistics ...
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Fly.io
        uses: superfly/flyctl-actions@master
        with:
          args: "deploy"
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
      
      - name: Verify deployment
        run: curl https://www.advocacyalawfirm.in/health
```

---

## 🚨 Troubleshooting

### App Won't Start
```bash
# Check logs
flyctl logs -a advocacy-law-firm

# Common issues:
# 1. Missing dependencies - check requirements.txt
# 2. Database connection - verify DATABASE_URL
# 3. Port conflict - ensure PORT=8000
```

### DNS Not Resolving
```bash
# Check DNS propagation
dig www.advocacyalawfirm.in

# Wait 24-48 hours for full propagation
```

### SSL Certificate Error
```bash
# Renew certificate
flyctl certs create www.advocacyalawfirm.in --force
```

### Frontend Not Loading
```bash
# Check if static files are served
curl https://www.advocacyalawfirm.in/static/law-firm.html

# Verify file path in app
ls -la static/law-firm.html
```

---

## 📈 Performance Optimization

### Enable Caching:
```python
from fastapi.middleware.gzip import GZIPMiddleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

### Add CDN (Cloudflare):
1. Point domain to Cloudflare
2. Enable caching rules
3. Set TTL for static files

### Database Connection Pooling:
```python
# Already configured in app.py
# Min: 1, Max: 5 connections
```

---

## 💰 Cost Estimates

### Fly.io:
- Shared CPU-1x, 256MB RAM: **$0.003/hour** (~$22/month)
- Always-on with monitoring: **$6/month**
- Total: ~**$30-50/month**

### Google Cloud Run:
- 1 CPU, 512MB RAM: **$0.000024/second** (~$20/month)
- Requests: **$0.40 per 1M requests**
- Total: ~**$25-50/month**

### AWS:
- t3.micro EC2: **$10/month**
- RDS db.t3.micro: **$15/month**
- ALB: **$20/month**
- Total: **$45-80/month**

---

## 🎯 Next Steps

1. **Choose deployment platform** (Fly.io recommended)
2. **Configure DNS records** at your registrar
3. **Set up SSL certificate**
4. **Deploy application**
5. **Run verification tests**
6. **Monitor in production**
7. **Set up email notifications** for consultations

---

## 📞 Support

For deployment help:
- **Email**: support@advocacyalawfirm.in
- **Documentation**: See README.md
- **API Docs**: https://www.advocacyalawfirm.in/docs

---

**Status**: Ready for Production  
**Version**: 1.0  
**Last Updated**: 2026-09-01

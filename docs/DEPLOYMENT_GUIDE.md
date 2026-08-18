# Kerdostat Full-Stack Production Deployment Guide

This guide provides step-by-step instructions for deploying the **Kerdostat Trading Platform** into production using Docker Compose, Nginx, Gunicorn, FastAPI, Redis, and SSL/TLS certificates.

---

## 1. System Requirements & Prerequisites

### Minimum Hardware Recommendations
* **CPU**: 2 vCPUs
* **RAM**: 4 GB RAM minimum (8 GB recommended for heavy WebSocket streaming)
* **Disk**: 20 GB SSD storage
* **OS**: Ubuntu 22.04 LTS / 24.04 LTS (or Debian 12)

### Required Server Software
* **Docker Engine** (v24.0+)
* **Docker Compose Plugin** (v2.20+)
* **Git**

To install Docker & Docker Compose on Ubuntu:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

---

## 2. Server Setup & Repository Clone

1. Clone the repository on your production cloud server:
   ```bash
   git clone https://github.com/shreya0x123/kerdostat.git /opt/kerdostat
   cd /opt/kerdostat
   ```

2. Create your production `.env` file from the provided template:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` to configure production secrets:
   ```bash
   nano .env
   ```

   Ensure you configure:
   - `ENVIRONMENT=production`
   - `JWT_SECRET`: Generate a secure secret key:
     ```bash
     openssl rand -hex 32
     ```
   - `ALLOWED_ORIGINS`: Set your production domain URL (e.g. `https://trading.yourdomain.com`).
   - `WORKERS`: Number of Gunicorn worker processes (Recommended: `2 * CPU cores + 1`).
   - Broker API credentials (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `FYERS_APP_ID`, `FYERS_ACCESS_TOKEN`).

---

## 3. Launching Production Stack via Docker Compose

Build and launch all containerized services (Redis, Backend Gunicorn cluster, Nginx reverse proxy):

```bash
docker compose up --build -d
```

### Verify Container Status & Health
```bash
docker compose ps
```

Check logs for any service:
```bash
# View backend logs
docker compose logs -f backend

# View Nginx logs
docker compose logs -f nginx

# View Redis logs
docker compose logs -f redis
```

---

## 4. Database Options & Production Migrations

### Option A: SQLite (Default Container Volume)
For low-to-medium volume, the SQLite database is automatically persisted inside the `backend_data` volume and migrated on startup by `backend/entrypoint.sh`.

### Option B: Managed PostgreSQL (Recommended for High Scale)
1. Provision a PostgreSQL instance (AWS RDS, DigitalOcean Managed Database, or self-hosted container).
2. Update `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://kerdostat_user:strong_password@postgres_host:5432/kerdostat_db
   ```
3. Restart the backend container:
   ```bash
   docker compose restart backend
   ```
   `entrypoint.sh` will automatically run `alembic upgrade head` on your PostgreSQL database.

---

## 5. SSL/TLS Certificate Setup (HTTPS)

To secure your production domain with free Let's Encrypt SSL certificates using Certbot:

1. Install Certbot on the host machine:
   ```bash
   sudo apt-get update
   sudo apt-get install -y certbot python3-certbot-nginx
   ```

2. Stop Nginx container temporarily for certificate issuance:
   ```bash
   docker compose stop nginx
   ```

3. Obtain SSL certificate:
   ```bash
   sudo certbot certonly --standalone -d trading.yourdomain.com
   ```

4. Map SSL certificates into `docker/nginx/nginx.conf` and `docker-compose.yml`:
   Certificates are located at:
   - Certificate: `/etc/letsencrypt/live/trading.yourdomain.com/fullchain.pem`
   - Private Key: `/etc/letsencrypt/live/trading.yourdomain.com/privkey.pem`

5. Restart stack:
   ```bash
   docker compose up -d nginx
   ```

---

## 6. Maintenance & Updates

### Updating Application Code
When deploying a new release:

```bash
cd /opt/kerdostat
git pull origin main
docker compose up --build -d
```

### Database Backup
To backup the SQLite database:
```bash
docker compose exec backend sqlite3 /app/kerdostat.db ".backup '/app/data/backup_$(date +%F).db'"
```

To backup PostgreSQL:
```bash
pg_dump -h postgres_host -U kerdostat_user kerdostat_db > kerdostat_backup_$(date +%F).sql
```

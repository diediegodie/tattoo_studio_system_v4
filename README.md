# Tattoo Studio System

## Project
Management system for tattoo studios, with Flask backend, PostgreSQL database, Google OAuth authentication and responsive frontend.

## Structure
- **backend/**: Python Flask code, SQLAlchemy models, authentication, routes and business logic
- **frontend/**: HTML templates, CSS, JS, system pages
- **docker-compose.yml**: Services orchestration
- **requirements.txt**: Python dependencies
- **.env**: Environment variables (credentials, URLs)

## Quick Installation
1. Install Docker and Docker Compose
2. **IMPORTANT**: Copy and configure the environment file:
   ```bash
   cp .env.example .env
   ```
3. Edit the `.env` file with your real credentials:
   - Configure Google OAuth credentials (see section below)
   - Change default database passwords
   - Configure a secure secret key for Flask
4. Start the services:
   ```bash
   docker compose up -d --build
   ```
5. Access the system at `http://localhost:5000/`

## Google OAuth Authentication
1. Access the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the APIs: Google+ API and Google Identity API
4. Configure OAuth 2.0 credentials:
   - Type: Web Application
   - Authorized redirect URIs:
     - `http://localhost:5000/auth/google/authorized`
     - `http://127.0.0.1:5000/auth/google/authorized`
5. Copy the Client ID and Client Secret to the `.env` file

## Database
- PostgreSQL
- Tables created automatically (`users`, `oauth`)
- To query users:
	```bash
	docker compose exec db psql -U admin -d tattoo_studio -c "SELECT id, name, email FROM users;"
	```

## Main Endpoints
- `/` or `/login`: Login page
- `/index`: Dashboard (protected)
- `/auth/login`: Start OAuth
- `/auth/logout`: Logout
- Other pages: inventory, sessions, financial, statement, internal registration, calculator, history

## Useful Commands
- Start: `docker compose up -d --build`
- Stop: `docker compose down`
- Logs: `docker compose logs app -f`
- Query database: `docker compose exec db psql -U admin -d tattoo_studio`

## Future Implementations
- [ ] Additional system features
- [ ] Integration with other payment methods
- [ ] Advanced reports and dashboards
- [ ] Notifications and alerts
- [ ] User permission customization
- [ ] Automated backup and restore


---

## 🐳 DOCKER COMMANDS - COMPLETE MANAGEMENT

### 🚀 **START APPLICATION**
```bash
# Start all services (app + database)
docker compose up -d --build

# Or start without rebuild (faster after first time)
docker compose up -d

# Start only the database
docker compose up -d db

# Start only the application
docker compose up -d app
```

### 🛑 **STOP APPLICATION**
```bash
# Stop all services
docker compose down

# Stop and remove volumes (CAUTION: deletes database data!)
docker compose down -v

# Stop only the application (keeps database running)
docker compose stop app

# Stop only the database
docker compose stop db
```

### 📊 **MONITORING AND LOGS**
```bash
# View application logs in real time
docker compose logs app -f

# View database logs
docker compose logs db -f

# View logs from all services
docker compose logs -f

# View container status
docker compose ps

# View detailed status
docker ps
```

### 🔧 **DATABASE MANAGEMENT**
```bash
# Access PostgreSQL terminal
docker compose exec db psql -U admin -d tattoo_studio

# Query users directly
docker compose exec db psql -U admin -d tattoo_studio -c "SELECT id, name, email FROM users;"

# Database backup
docker compose exec db pg_dump -U admin tattoo_studio > backup.sql

# Restore backup
docker compose exec -T db psql -U admin -d tattoo_studio < backup.sql
```

### 🔄 **RESTART SERVICES**
```bash
# Restart application
docker compose restart app

# Restart database
docker compose restart db

# Restart all services
docker compose restart
```

### 🧹 **CLEANUP AND MAINTENANCE**
```bash
# Complete rebuild (force recreation)
docker compose up -d --build --force-recreate

# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Complete cleanup (CAUTION!)
docker system prune -a
```

### 🔍 **DEBUG AND TROUBLESHOOTING**
```bash
# Access application terminal
docker compose exec app bash

# Check application environment variables
docker compose exec app env

# View resource usage
docker stats

# Inspect specific container
docker inspect tattoo_studio_app
docker inspect tattoo_studio_db
```

### 📱 **QUICK ACCESS**
```bash
# Open application in browser (Linux)
xdg-open http://localhost:5000

# View summarized logs (last 50 lines)
docker compose logs app --tail=50
```

### 🎯 **MOST USED DAILY COMMANDS:**
```bash
# 1. Start everything
docker compose up -d --build

# 2. Check if it's working
docker compose ps

# 3. View logs if there's a problem
docker compose logs app -f

# 4. Stop everything
docker compose down
```

---
This README serves as a quick guide for installation, configuration and system usage. Add future implementations and observations below as the project evolves.


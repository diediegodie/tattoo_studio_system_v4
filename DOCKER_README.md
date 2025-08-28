# Docker Setup Guide

This project uses a multi-stage Dockerfile that supports development, production, and testing environments.

## Dockerfile Stages

### Base Stage
- Common setup with Python 3.11, system dependencies, and Python packages
- Sets proper working directory to `/app/app` for correct Python path resolution
- Includes security hardening with non-root user

### Development Stage (`development`)
- Extends base stage with Flask development tools
- Enables hot reloading and debug mode
- Uses Flask CLI for development server

### Production Stage (`production`)
- Extends base stage with Gunicorn WSGI server
- Optimized for production performance and security
- Includes health checks and proper worker configuration

### Test Stage (`test`)
- Extends base stage with testing dependencies
- Configured for running pytest with coverage
- Isolated test environment

## Usage

### Development

```bash
# Start development environment
docker-compose up app

# Or specify explicitly
DOCKER_TARGET=development docker-compose up app
```

### Production

```bash
# Start production environment
DOCKER_TARGET=production docker-compose up app
```

### Testing

```bash
# Run tests with docker-compose
docker-compose -f docker-compose.test.yml up test-runner

# Or build and run manually
docker build --target test -t tattoo-studio-test .
docker run --rm tattoo-studio-test
```

## Environment Variables

### Required
- `DATABASE_URL`: PostgreSQL connection string
- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret

### Optional
- `FLASK_ENV`: Environment (development/production/testing)
- `FLASK_DEBUG`: Debug mode (1/0)
- `DOCKER_TARGET`: Docker build target (development/production/test)

## Key Improvements

1. **Proper WORKDIR**: Set to `/app/app` to match Python import paths
2. **No Shell Commands**: Uses native Docker CMD syntax
3. **Multi-Stage**: Separate optimized images for each environment
4. **SOLID Compliance**: Maintains existing architecture and imports
5. **Security**: Non-root user and minimal attack surface
6. **Performance**: Layer caching and production optimizations

## File Structure

```
backend/
├── Dockerfile          # Multi-stage Dockerfile
├── app/               # Flask application
├── tests/             # Test suite
└── pytest.ini         # Test configuration

frontend/              # Static assets
docker-compose.yml     # Development/Production
docker-compose.test.yml # Testing
.dockerignore          # Build optimization
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure:
- WORKDIR is set to `/app/app` in the container
- PYTHONPATH includes `/app`
- All relative imports use the correct paths

### Database Connection
- Ensure PostgreSQL container is healthy before starting the app
- Check DATABASE_URL environment variable
- Verify network connectivity between containers

### Permission Issues
- The container runs as non-root user `appuser`
- Ensure proper file permissions for mounted volumes

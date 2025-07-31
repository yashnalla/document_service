# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django document service built with Python 3.11, Poetry for dependency management, and Docker for containerization. The project uses PostgreSQL as its primary database with Redis for caching and is designed to support Lexical editor content storage with document versioning.

## Development Environment

### Quick Setup
```bash
make dev-setup    # Complete development setup (build, start, migrate)
make up           # Start services
make logs         # View logs
```

### Essential Commands

**Development workflow:**
- `make shell` - Access Django shell
- `make bash` - Access container bash shell
- `make migrate` - Run database migrations
- `make makemigrations` - Create new migrations
- `make check` - Run Django system checks
- `make createsuperuser` - Create Django superuser

**Code quality:**
- `make test` - Run tests with pytest
- `make test-coverage` - Run tests with coverage reporting
- `make lint` - Check code formatting with black
- `make format` - Format code with black

**Docker management:**
- `make build` - Build containers
- `make down` - Stop containers
- `make restart` - Restart services
- `make ps` - Show running containers
- `make clean` - Clean up containers and images
- `make dev-reset` - Reset entire environment

**Poetry dependency management:**
- `make poetry-lock` - Generate poetry.lock file
- `make poetry-install` - Install dependencies
- `make poetry-update` - Update dependencies
- `make poetry-show` - Show installed packages

**Single test execution:**
```bash
docker-compose exec web poetry run pytest path/to/test_file.py::test_function_name
```

## Architecture

### Multi-Service Architecture
The application runs as a multi-container setup:
- **web**: Django application server (port 8000)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)

All services are orchestrated via docker-compose with the web service depending on both postgres and redis.

### Document Model Design
The core `Document` model (`documents/models.py`) is designed for collaborative document editing:
- **UUID primary keys** for distributed system compatibility
- **JSONField content** optimized for Lexical editor state storage
- **Version tracking** with integer version field
- **User relationships** via foreign key to Django's User model
- **Temporal tracking** with created_at/updated_at timestamps

### Configuration Strategy
- **Environment-based configuration** using python-dotenv
- **Settings loaded from `.env` file** (created from `.env.example`)
- **Multi-database support**: PostgreSQL for primary data, Redis for caching
- **Container-aware settings**: Database/Redis hosts reference service names

### Docker and Poetry Integration
- **Poetry dependencies installed directly** into container (no virtual environment)
- **Development volume mounting** for live code reloading
- **Automatic lock file generation** when missing during build
- **Multi-stage compatible** Dockerfile ready for production builds

## Database Architecture

### PostgreSQL Primary Database
- **Engine**: `django.db.backends.postgresql`
- **Connection**: Environment-variable driven (POSTGRES_DB, POSTGRES_USER, etc.)
- **Data persistence**: Named volume `postgres_data`

### Redis Caching Layer
- **Backend**: `django.core.cache.backends.redis.RedisCache`
- **Connection**: Via REDIS_URL environment variable
- **Usage**: General purpose caching, session storage ready

### Migration Handling
All database migrations are handled via Django's migration system. The container is configured to run migrations on startup via the Dockerfile CMD.

## Health Monitoring

The application includes a health check endpoint at `/health/` that verifies:
- Database connectivity (PostgreSQL)
- Cache connectivity (Redis)
- Returns JSON status with service health information

## Testing Framework

Uses pytest as the testing framework with coverage reporting available via pytest-cov plugin. Tests run inside the Docker container to match the production environment.

## Code Style

Uses Black for code formatting with default settings. All code should be formatted before commits using `make format`.

## API Architecture

### REST API Design
The API follows Django REST Framework conventions:
- **Base URL**: `/api/` for all API endpoints
- **Document endpoints**: `/api/documents/` (CRUD operations)
- **Health endpoint**: `/health/` for system monitoring
- **Admin interface**: `/admin/` for Django admin

### Permission Model
- **Default permission**: `IsAuthenticatedOrReadOnly` (documents/views.py:13)
- **Anonymous users**: Can read documents, create through fallback "anonymous" user
- **Search functionality**: Query parameter `?search=term` searches title and content

### Serializer Strategy
Three specialized serializers for different use cases:
- **DocumentListSerializer**: Lightweight for list views (excludes content)
- **DocumentSerializer**: Full document details for retrieve/update
- **DocumentCreateSerializer**: Validation-focused for creation with anonymous user handling

## Development Workflow

### Environment Setup
1. Copy `.env.example` to `.env` and configure
2. Run `make dev-setup` for complete initialization
3. Use `make dev-setup-fresh` to include default admin user (admin/admin123)

### Testing Strategy
- **Test files**: `test_simple.py`, `test_api.py` for API testing
- **Framework**: pytest with coverage support
- **Container testing**: All tests run inside Docker for environment consistency
- **Manual testing**: Use provided test scripts or Django shell

### Database Operations
**PostgreSQL-specific commands:**
- `make db-shell` - Direct PostgreSQL access
- `make db-reset` - Dangerous: drops all data and recreates schema  
- `make backup` - Creates timestamped SQL dumps
- `make restore BACKUP_FILE=filename` - Restores from backup

**Redis operations:**
- `make redis-cli` - Access Redis command line
- `make redis-monitor` - Real-time command monitoring
- `make redis-flush` - Clear all cache data

## Important Notes

- **All database commands are now PostgreSQL-compatible** - backup, restore, reset all work with PostgreSQL
- **Redis commands available** - monitor, info, flush commands for cache management
- **Health monitoring** - dedicated `/health/` endpoint and `make health` command
- **The project uses UUID primary keys** for the Document model to support distributed scenarios
- **JSONField content storage** is specifically designed for Lexical editor integration
- **Environment verification** - `make env-check` validates configuration settings
- **Anonymous user handling**: Documents created without authentication use fallback "anonymous" user
- **Version tracking**: Document model automatically increments version on content/title changes
.PHONY: help build up down restart logs shell test lint format check migrate makemigrations createsuperuser collectstatic clean prune health logs-web logs-postgres logs-redis bash-postgres redis-cli db-reset db-shell db-migrate-fresh backup restore db-size dev-setup-fresh redis-monitor redis-info redis-flush show-urls tail-logs env-check perf-test perf-test-search perf-test-large perf-test-fast perf-test-baseline perf-report perf-install perf-clean

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Docker commands
build: ## Build the Docker containers
	docker-compose build

up: ## Start the services in detached mode
	docker-compose up -d

down: ## Stop and remove containers
	docker-compose down

restart: ## Restart the services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-web: ## View logs from web service only
	docker-compose logs -f web

logs-postgres: ## View logs from postgres service only
	docker-compose logs -f postgres

logs-redis: ## View logs from redis service only
	docker-compose logs -f redis

# Development commands
shell: ## Access Django shell inside container
	docker-compose exec web python manage.py shell

bash: ## Access bash shell inside container
	docker-compose exec web bash

bash-postgres: ## Access postgres container bash shell
	docker-compose exec postgres bash

redis-cli: ## Access Redis CLI
	docker-compose exec redis redis-cli

# Django commands
migrate: ## Run Django migrations
	docker-compose exec web python manage.py migrate

makemigrations: ## Create new Django migrations
	docker-compose exec web python manage.py makemigrations

createsuperuser: ## Create Django superuser
	docker-compose exec web python manage.py createsuperuser

collectstatic: ## Collect static files
	docker-compose exec web python manage.py collectstatic --noinput

health: ## Check application health
	@echo "🔍 Checking application health..."
	@curl -s http://localhost:8000/health/ | python -m json.tool || echo "❌ Health check failed - is the server running?"

# Code quality
test: ## Run tests
	docker-compose exec web poetry run pytest

test-coverage: ## Run tests with coverage
	docker-compose exec web poetry run pytest --cov

lint: ## Run linting with black
	docker-compose exec web poetry run black --check .

format: ## Format code with black
	docker-compose exec web poetry run black .

check: ## Run Django system checks
	docker-compose exec web python manage.py check

# Poetry commands
lock: ## Generate poetry.lock file and install
	docker-compose exec web poetry lock
	docker-compose exec web poetry install


poetry-install: ## Install dependencies
	docker-compose exec web poetry install

poetry-update: ## Update dependencies
	docker-compose exec web poetry update

poetry-show: ## Show installed packages
	docker-compose exec web poetry show

# Database commands
db-reset: ## Reset database (WARNING: This will delete all data)
	@echo "⚠️  WARNING: This will delete ALL data in the database!"
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	docker-compose exec postgres psql -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-document_db} -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	docker-compose exec web python manage.py migrate

db-shell: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-document_db}

db-migrate-fresh: ## Drop all tables and run fresh migrations
	@echo "⚠️  WARNING: This will delete ALL data and recreate tables!"
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	docker-compose exec web python manage.py reset_db --noinput || true
	docker-compose exec web python manage.py migrate

# Utility commands
clean: ## Clean up Docker containers and images
	docker-compose down -v --remove-orphans
	docker system prune -f

prune: ## Remove all unused Docker objects
	docker system prune -a -f --volumes

# Development workflow
dev-setup: build up migrate lock ## Complete development setup
	@echo "🚀 Development environment is ready!"
	@echo "📝 Create a superuser with: make createsuperuser"
	@echo "🌐 Access the app at: http://localhost:8000"
	@echo "👑 Access admin at: http://localhost:8000/admin/"
	@echo "❤️  Health check at: http://localhost:8000/health/"
	@make health

dev-setup-fresh: ## Fresh development setup with superuser
	@make dev-setup
	@echo "👤 Creating superuser (admin/admin123)..."
	@docker-compose exec web python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
	@docker-compose exec web poetry run python manage.py create_test_users
dev-reset: down clean dev-setup-fresh ## Reset entire development environment

# Production-like commands
prod-build: ## Build for production
	docker-compose -f docker-compose.yml build

# Monitoring
ps: ## Show running containers
	docker-compose ps

top: ## Show running processes in containers
	docker-compose top

# Backup and restore (PostgreSQL)
backup: ## Backup PostgreSQL database
	@echo "📦 Creating database backup..."
	docker-compose exec postgres pg_dump -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-document_db} > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

restore: ## Restore PostgreSQL database from backup (specify BACKUP_FILE=filename)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Please specify BACKUP_FILE=filename"; \
		exit 1; \
	fi
	@echo "📥 Restoring database from $(BACKUP_FILE)..."
	@echo "⚠️  WARNING: This will overwrite existing data!"
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	docker-compose exec -T postgres psql -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-document_db} < $(BACKUP_FILE)
	@echo "✅ Database restored from $(BACKUP_FILE)"

db-size: ## Show database size information
	docker-compose exec postgres psql -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-document_db} -c "\l+"

# Redis commands
redis-monitor: ## Monitor Redis commands in real-time
	docker-compose exec redis redis-cli monitor

redis-info: ## Show Redis server information
	docker-compose exec redis redis-cli info

redis-flush: ## Flush all Redis data (WARNING: clears cache)
	@echo "⚠️  WARNING: This will clear all Redis cache data!"
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	docker-compose exec redis redis-cli flushall

# Search commands
search-reindex: ## Rebuild search vectors for all documents
	@echo "🔍 Rebuilding search vectors for all documents..."
	docker-compose exec web python manage.py update_search_vectors

search-stats: ## Show search index statistics and performance
	@echo "📊 Displaying search statistics..."
	docker-compose exec web python manage.py search_stats

search-test: ## Run search performance tests
	@echo "⚡ Running search performance tests..."
	docker-compose exec web python manage.py search_stats --test-search --verbose

search-reindex-force: ## Force rebuild all search vectors (even existing ones)
	@echo "🔄 Force rebuilding ALL search vectors..."
	docker-compose exec web python manage.py update_search_vectors --force

# WebSocket commands
daphne: ## Run the application with Daphne (WebSocket support)
	docker-compose exec web poetry run daphne -b 0.0.0.0 -p 8000 document_service.asgi:application

ws-test: ## Test WebSocket connectivity
	@echo "🔌 Testing WebSocket connectivity..."
	docker-compose exec web poetry run python manage.py test_websockets

ws-test-all: ## Run all WebSocket tests
	@echo "🔌 Running comprehensive WebSocket tests..."
	docker-compose exec web poetry run python manage.py test_websockets --test-type all

# Development utilities
show-urls: ## Show all Django URL patterns
	docker-compose exec web python manage.py show_urls

tail-logs: ## Tail logs from all services (non-following)
	docker-compose logs --tail=50

env-check: ## Verify environment configuration
	@echo "🔍 Checking environment configuration..."
	@docker-compose exec web python -c "import os; print('SECRET_KEY:', 'SET' if os.getenv('SECRET_KEY') else 'NOT SET'); print('DEBUG:', os.getenv('DEBUG', 'False')); print('POSTGRES_DB:', os.getenv('POSTGRES_DB', 'document_db')); print('REDIS_URL:', os.getenv('REDIS_URL', 'redis://redis:6379/0'))"

# Performance testing commands
perf-test: ## Run all performance tests
	@echo "🏃 Running all performance tests..."
	docker-compose exec web poetry run pytest performance_tests/ --runperformance -v

perf-test-search: ## Run search performance tests only
	@echo "🔍 Running search performance tests..."
	docker-compose exec web poetry run pytest performance_tests/test_search_performance.py --runperformance -v

perf-test-large: ## Run large document performance tests only
	@echo "📄 Running large document performance tests..."
	docker-compose exec web poetry run pytest performance_tests/test_large_documents.py --runperformance -v

perf-test-fast: ## Run only fast performance tests (skip slow/memory intensive)
	@echo "⚡ Running fast performance tests..."
	docker-compose exec web poetry run pytest performance_tests/ --runperformance -v -m "performance and not slow and not memory_intensive"

perf-test-baseline: ## Establish performance baseline
	@echo "📊 Establishing performance baseline..."
	docker-compose exec web poetry run pytest performance_tests/ --runperformance --performance-baseline -v

perf-report: ## Generate performance report
	@echo "📋 Generating performance report..."
	docker-compose exec web poetry run pytest performance_tests/ --runperformance --performance-report -v

perf-install: ## Install performance testing dependencies
	@echo "📦 Installing performance testing dependencies..."
	docker-compose exec web poetry install --with dev

perf-clean: ## Clean up performance test artifacts
	@echo "🧹 Cleaning up performance test artifacts..."
	docker-compose exec web find performance_tests/reports/ -name "*.json" -not -name ".gitkeep" -delete || true
	docker-compose exec web find performance_tests/reports/ -name "*.html" -delete || true
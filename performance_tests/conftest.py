"""
Performance test configuration and fixtures.

This module provides pytest configuration and fixtures specifically
optimized for performance testing with timing, memory profiling,
and large document generation capabilities.
"""

import pytest
import uuid
import os
import tempfile
from typing import Callable, Dict, Any

# Ensure Django is configured before importing Django modules
import django
from django.conf import settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_service.settings')
    django.setup()

from django.contrib.auth.models import User
from django.test import override_settings
from django.core.management import call_command
from django.db import transaction
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from documents.models import Document
from .utils.generators import DocumentContentGenerator
from .utils.benchmarks import PerformanceBenchmark
from .utils.profiling import MemoryProfiler


# Performance test markers
def pytest_configure(config):
    """Configure pytest markers for performance tests."""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "memory_intensive: mark test as memory intensive"
    )


# Performance test database settings
@pytest.fixture(scope="session")
def performance_db_settings():
    """Database settings optimized for performance testing."""
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'document_db'),  # Use the same database for now
        'USER': os.getenv('POSTGRES_USER', 'user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'password'),
        'HOST': os.getenv('POSTGRES_HOST', 'postgres'),  # Use docker service name
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            # Performance optimizations for testing
            'options': '-c synchronous_commit=off -c fsync=off -c full_page_writes=off'
        }
    }


# Database setup is handled by pytest-django automatically


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all performance tests.
    This fixture is applied to all tests automatically.
    """
    pass


# User fixtures
@pytest.fixture
def perf_user():
    """Create a test user for performance tests."""
    return User.objects.create_user(
        username=f"perfuser_{uuid.uuid4().hex[:8]}",
        email="perfuser@example.com",
        password="perfpass123",
        first_name="Performance",
        last_name="User"
    )


@pytest.fixture
def perf_admin_user():
    """Create an admin user for performance tests."""
    return User.objects.create_superuser(
        username=f"perfadmin_{uuid.uuid4().hex[:8]}",
        email="perfadmin@example.com",
        password="perfadmin123",
        first_name="Performance",
        last_name="Admin"
    )


@pytest.fixture
def perf_anonymous_user():
    """Get or create anonymous user for performance tests."""
    user, created = User.objects.get_or_create(
        username="anonymous",
        defaults={
            "first_name": "Anonymous",
            "last_name": "User",
            "email": "anonymous@example.com",
        },
    )
    return user


# API client fixtures
@pytest.fixture
def perf_api_client():
    """Create an API client for performance tests."""
    return APIClient()


@pytest.fixture
def perf_authenticated_client(perf_api_client, perf_user):
    """Create an authenticated API client for performance tests."""
    perf_api_client.force_authenticate(user=perf_user)
    return perf_api_client


@pytest.fixture
def perf_user_token(perf_user):
    """Create an API token for performance test user."""
    token, created = Token.objects.get_or_create(user=perf_user)
    return token


# Content generation fixtures
@pytest.fixture
def content_generator():
    """Create a document content generator."""
    return DocumentContentGenerator()


@pytest.fixture
def small_document_content(content_generator):
    """Generate small document content (1KB)."""
    return content_generator.generate_content(size_kb=1)


@pytest.fixture
def medium_document_content(content_generator):
    """Generate medium document content (100KB)."""
    return content_generator.generate_content(size_kb=100)


@pytest.fixture
def large_document_content(content_generator):
    """Generate large document content (1MB)."""
    return content_generator.generate_content(size_mb=1)


@pytest.fixture
def xlarge_document_content(content_generator):
    """Generate extra large document content (10MB)."""
    return content_generator.generate_content(size_mb=10)


@pytest.fixture
def huge_document_content(content_generator):
    """Generate huge document content (50MB)."""
    return content_generator.generate_content(size_mb=50)


@pytest.fixture
def massive_document_content(content_generator):
    """Generate massive document content (100MB)."""
    return content_generator.generate_content(size_mb=100)


# Document factory fixtures
@pytest.fixture
def perf_document_factory(perf_user):
    """Factory for creating performance test documents."""
    def _create_document(title=None, content=None, size_mb=None, size_kb=None, created_by=None):
        if created_by is None:
            created_by = perf_user
        
        if title is None:
            title = f"Performance Test Document {uuid.uuid4().hex[:8]}"
        
        if content is None and (size_mb or size_kb):
            generator = DocumentContentGenerator()
            if size_mb:
                content = generator.generate_content(size_mb=size_mb)
            else:
                content = generator.generate_content(size_kb=size_kb)
        elif content is None:
            content = "Default performance test content"
        
        return Document.objects.create(
            title=title,
            content=content,
            created_by=created_by,
        )
    
    return _create_document


@pytest.fixture
def bulk_document_factory(perf_user, content_generator):
    """Factory for creating multiple documents efficiently."""
    def _create_documents(count: int, size_kb: int = 1, title_prefix: str = "Bulk Doc"):
        documents = []
        content = content_generator.generate_content(size_kb=size_kb)
        
        # Use bulk_create for efficiency
        document_objects = []
        for i in range(count):
            document_objects.append(Document(
                title=f"{title_prefix} {i+1}",
                content=content,
                created_by=perf_user,
            ))
        
        # Bulk create in batches of 100 to avoid memory issues
        batch_size = 100
        for i in range(0, len(document_objects), batch_size):
            batch = document_objects[i:i + batch_size]
            created_docs = Document.objects.bulk_create(batch)
            documents.extend(created_docs)
        
        return documents
    
    return _create_documents


# Search corpus fixtures
@pytest.fixture
def small_search_corpus(bulk_document_factory):
    """Create a small search corpus (100 documents)."""
    return bulk_document_factory(count=100, size_kb=5, title_prefix="Search Test")


@pytest.fixture
def medium_search_corpus(bulk_document_factory):
    """Create a medium search corpus (1,000 documents)."""
    return bulk_document_factory(count=1000, size_kb=10, title_prefix="Search Corpus")


@pytest.fixture
def large_search_corpus(bulk_document_factory):
    """Create a large search corpus (10,000 documents)."""
    return bulk_document_factory(count=10000, size_kb=5, title_prefix="Large Corpus")


# Benchmark and profiling fixtures
@pytest.fixture
def benchmark_timer():
    """Create a high-precision benchmark timer."""
    return PerformanceBenchmark()


@pytest.fixture
def memory_profiler():
    """Create a memory usage profiler."""
    return MemoryProfiler()


@pytest.fixture
def performance_thresholds():
    """Define performance thresholds for tests."""
    return {
        # Search performance thresholds
        'search_indexing_1mb': 0.05,      # 50ms for 1MB document indexing
        'search_indexing_10mb': 0.5,      # 500ms for 10MB document indexing
        'bulk_indexing_1000': 10.0,       # 10s for 1000 documents
        'search_query_large_corpus': 0.02, # 20ms for search query
        'search_vector_update': 0.03,      # 30ms for search vector update
        
        # Large document thresholds
        'large_doc_creation_10mb': 0.5,    # 500ms for 10MB document creation
        'large_doc_creation_50mb': 2.0,    # 2s for 50MB document creation
        'large_doc_creation_100mb': 5.0,   # 5s for 100MB document creation
        'large_doc_save_load_10mb': 1.0,   # 1s for 10MB document save/load
        'large_doc_search_index_100mb': 2.0, # 2s for 100MB document search indexing
        
        # Memory thresholds (in MB)
        'memory_10mb_doc': 50,             # 50MB memory for 10MB document
        'memory_100mb_doc': 200,           # 200MB memory for 100MB document
        'memory_bulk_1000_docs': 100,      # 100MB memory for 1000 documents
    }


# Data persistence - no cleanup to keep test documents in database


# Session persistence - no cleanup to keep test documents in database


# Pytest collection hook to skip performance tests by default and add database access
def pytest_collection_modifyitems(config, items):
    """Skip performance tests unless explicitly requested and add database access markers."""
    if not config.getoption("--runperformance"):
        skip_performance = pytest.mark.skip(reason="Performance tests skipped (use --runperformance to run)")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_performance)
    else:
        # Add django_db marker to all performance tests (no transaction rollback to persist data)
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(pytest.mark.django_db)


def pytest_addoption(parser):
    """Add command line options for performance tests."""
    parser.addoption(
        "--runperformance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--performance-baseline",
        action="store_true", 
        default=False,
        help="Establish performance baseline"
    )
    parser.addoption(
        "--performance-report",
        action="store_true",
        default=False,
        help="Generate performance report"
    )
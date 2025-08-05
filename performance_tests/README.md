# Performance Testing Framework

This directory contains a comprehensive performance testing framework for the document service, focusing on search functionality and large document handling.

## Overview

The performance testing framework is designed to:
- Test search indexing and query performance
- Validate large document handling capabilities  
- Monitor memory usage and detect memory leaks
- Provide benchmarking and regression detection
- Generate detailed performance reports

## Architecture

```
performance_tests/
├── __init__.py                     # Package initialization
├── conftest.py                     # pytest configuration and fixtures
├── test_search_performance.py      # Search performance tests
├── test_large_documents.py         # Large document handling tests
├── utils/
│   ├── __init__.py
│   ├── generators.py               # Test data generation utilities
│   ├── benchmarks.py               # Benchmark measurement tools
│   └── profiling.py                # Memory and CPU profiling utilities
├── reports/                        # Generated performance reports
│   └── .gitkeep
└── README.md                       # This file
```

## Quick Start

### 1. Install Dependencies

```bash
make perf-install
```

This installs the required performance testing dependencies:
- `pytest-benchmark` - Precise performance measurement
- `memory-profiler` - Memory usage tracking  
- `psutil` - System resource monitoring

### 2. Run Performance Tests

```bash
# Run all performance tests
make perf-test

# Run only search performance tests
make perf-test-search

# Run only large document tests
make perf-test-large

# Run fast tests only (skip slow/memory intensive)
make perf-test-fast
```

### 3. Establish Baseline

```bash
# Establish performance baseline for future comparisons
make perf-test-baseline
```

### 4. Generate Reports

```bash
# Generate detailed performance report
make perf-report
```

## Test Categories

### Search Performance Tests (`test_search_performance.py`)

#### TestSearchIndexingPerformance
- **Document Indexing**: Tests indexing performance for documents from 1KB to 10MB
- **Performance Thresholds**: < 50ms for 1MB document, < 500ms for 10MB document
- **Memory Monitoring**: Tracks memory usage during indexing operations

#### TestBulkSearchIndexing  
- **Bulk Operations**: Tests bulk indexing of 100-10,000 documents
- **Performance Thresholds**: < 10 seconds for 1,000 documents
- **Memory Validation**: Ensures reasonable memory usage during bulk operations

#### TestSearchQueryPerformance
- **Query Performance**: Tests search queries against corpora of 100-10,000 documents
- **Performance Thresholds**: < 20ms per query for large corpus
- **Scalability Testing**: Validates performance scales well with corpus size

#### TestSearchVectorUpdates
- **Update Performance**: Tests search vector updates after content changes
- **Batch Updates**: Tests performance of batch search vector updates
- **Performance Thresholds**: < 30ms per update

### Large Document Tests (`test_large_documents.py`)

#### TestLargeDocumentCreation
- **Document Sizes**: Tests creation of 1MB, 10MB
- **Performance Thresholds**: < 500ms for 10MB
- **Memory Monitoring**: Comprehensive memory usage tracking
- **Garbage Collection**: Monitors GC impact on large operations

#### TestLargeDocumentOperations
- **Save/Load Performance**: Tests database operations with large documents
- **Content Updates**: Tests updating large document content
- **Version Control**: Tests version management with large documents

#### TestLargeDocumentScalability
- **Size Scalability**: Tests how performance scales with document size
- **Concurrent Operations**: Simulates concurrent operations on large documents
- **Efficiency Analysis**: Measures scaling efficiency and bottlenecks

## Performance Thresholds

The framework defines performance thresholds in `conftest.py`:

```python
performance_thresholds = {
    # Search performance thresholds
    'search_indexing_1mb': 0.05,           # 50ms for 1MB document indexing
    'search_indexing_10mb': 0.5,           # 500ms for 10MB document indexing
    'bulk_indexing_1000': 10.0,            # 10s for 1000 documents
    'search_query_large_corpus': 0.02,     # 20ms for search query
    'search_vector_update': 0.03,          # 30ms for search vector update
    
    # Large document thresholds
    'large_doc_creation_10mb': 0.5,        # 500ms for 10MB document creation
    'large_doc_creation_50mb': 2.0,        # 2s for 50MB document creation
    'large_doc_creation_100mb': 5.0,       # 5s for 100MB document creation
    'large_doc_search_index_100mb': 2.0,   # 2s for 100MB document search indexing
    
    # Memory thresholds (in MB)
    'memory_10mb_doc': 50,                 # 50MB memory for 10MB document
    'memory_100mb_doc': 200,               # 200MB memory for 100MB document
    'memory_bulk_1000_docs': 100,          # 100MB memory for 1000 documents
}
```

## Test Markers

The framework uses pytest markers to categorize tests:

- `@pytest.mark.performance` - All performance tests
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.memory_intensive` - Tests that use significant memory

## Running Specific Test Categories

```bash
# Run only fast performance tests
pytest performance_tests/ --runperformance -m "performance and not slow"

# Run only memory intensive tests  
pytest performance_tests/ --runperformance -m "memory_intensive"

# Run specific test class
pytest performance_tests/test_search_performance.py::TestSearchIndexingPerformance --runperformance

# Run specific test method
pytest performance_tests/test_large_documents.py::TestLargeDocumentCreation::test_create_large_document_10mb --runperformance
```

## Utilities

### Test Data Generators (`utils/generators.py`)

- **DocumentContentGenerator**: Generates realistic content of various sizes and types
- **SearchQueryGenerator**: Creates realistic search queries for testing
- **DocumentCorpusGenerator**: Generates large document corpora for testing

### Benchmark Tools (`utils/benchmarks.py`)

- **PerformanceBenchmark**: High-precision timing and statistical analysis
- **PerformanceRegression**: Detects performance regressions between runs
- **PerformanceReporter**: Generates HTML and JSON performance reports

### Profiling Tools (`utils/profiling.py`)

- **MemoryProfiler**: Tracks memory usage and detects memory leaks
- **CPUProfiler**: Monitors CPU usage during tests
- **ResourceProfiler**: Combined memory and CPU profiling

## Configuration

### Database Settings

Performance tests use a separate database optimized for testing:
- Database name: `{POSTGRES_DB}_perf_test`
- Optimized settings for performance testing
- Automatic cleanup after test sessions


## Interpreting Results

### Benchmark Output

```
Benchmark: search_indexing_1mb
Iterations: 20
Mean time: 0.0234s
Median time: 0.0231s
95th percentile: 0.0267s
Std deviation: 0.0012s
Operations/sec: 42.74
```

### Memory Profiling

```
Memory Usage: Peak 45.67MB, Delta 12.34MB
```

### Performance Assertions

Tests automatically fail if performance thresholds are exceeded:
```
AssertionError: Performance thresholds not met for search_indexing_10mb:
Mean time 0.7234s exceeds threshold 0.5000s
```

## Troubleshooting

### Memory Issues

If you encounter memory issues:
```bash
# Run only fast tests
make perf-test-fast

# Clean up test artifacts
make perf-clean

# Check system resources
docker stats
```

### Database Issues

If performance database setup fails:
```bash
# Reset and recreate databases
make db-reset
make migrate
```

### Slow Tests

To skip slow tests during development:
```bash
pytest performance_tests/ --runperformance -m "performance and not slow"
```


## Extending the Framework

To add new performance tests:

1. Create test methods with `@pytest.mark.performance`
2. Use provided fixtures for test data generation
3. Use benchmark utilities for timing measurements
4. Use profiling utilities for resource monitoring
5. Define appropriate performance thresholds
6. Clean up test data to avoid interference


## Quick Start Example

```bash
# Install dependencies and run fast tests
make perf-install
make perf-test-fast

# Results will show benchmark statistics like:
# 1KB Document Indexing: Mean time: 0.0234s, Operations/sec: 42.74
# Memory Usage: Peak 45.67MB, Delta 12.34MB
```
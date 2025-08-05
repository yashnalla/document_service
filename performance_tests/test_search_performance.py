"""
Search performance tests for the document service.

This module contains comprehensive performance tests for search functionality,
including indexing performance, query performance, and bulk operations.
"""

import pytest
import time
from typing import List
from django.core.management import call_command
from documents.models import Document
from documents.services import DocumentService
from .utils.generators import SearchQueryGenerator
from .utils.benchmarks import PerformanceBenchmark
from .utils.profiling import MemoryProfiler, ResourceProfiler


@pytest.mark.performance
class TestSearchIndexingPerformance:
    """Test search indexing performance for various document sizes."""
    
    def test_search_indexing_small_document_1kb(self, perf_document_factory, 
                                               perf_user, benchmark_timer, 
                                               performance_thresholds):
        """Test search indexing performance for 1KB document."""
        
        def create_and_index_document():
            doc = perf_document_factory(
                title="Small Document Performance Test",
                size_kb=1,
                created_by=perf_user
            )
            doc.update_search_vector()
            return doc
        
        result = benchmark_timer.benchmark_function(
            create_and_index_document,
            iterations=100,
            name="search_indexing_1kb",
            document_size="1KB"
        )
        
        # Assert performance threshold
        benchmark_timer.assert_performance_threshold(
            result, 
            max_mean_time=performance_thresholds['search_indexing_1mb'],  # Use 1MB threshold for 1KB (should be much faster)
            max_percentile_95=performance_thresholds['search_indexing_1mb'] * 1.5
        )
        
        print(f"1KB Document Indexing: {result}")
    
    def test_search_indexing_medium_document_100kb(self, perf_document_factory, 
                                                  perf_user, benchmark_timer,
                                                  performance_thresholds):
        """Test search indexing performance for 100KB document."""
        
        def create_and_index_document():
            doc = perf_document_factory(
                title="Medium Document Performance Test",
                size_kb=100,
                created_by=perf_user
            )
            doc.update_search_vector()
            return doc
        
        result = benchmark_timer.benchmark_function(
            create_and_index_document,
            iterations=50,
            name="search_indexing_100kb",
            document_size="100KB"
        )
        
        # Assert performance threshold
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['search_indexing_1mb'],
            max_percentile_95=performance_thresholds['search_indexing_1mb'] * 1.5
        )
        
        print(f"100KB Document Indexing: {result}")
    
    @pytest.mark.slow
    def test_search_indexing_large_document_1mb(self, perf_document_factory, 
                                               perf_user, benchmark_timer,
                                               performance_thresholds):
        """Test search indexing performance for 1MB document."""
        
        def create_and_index_document():
            doc = perf_document_factory(
                title="Large Document Performance Test",
                size_mb=1,
                created_by=perf_user
            )
            doc.update_search_vector()
            return doc
        
        result = benchmark_timer.benchmark_function(
            create_and_index_document,
            iterations=20,
            name="search_indexing_1mb",
            document_size="1MB"
        )
        
        # Assert performance threshold
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['search_indexing_1mb'],
            max_percentile_95=performance_thresholds['search_indexing_1mb'] * 2
        )
        
        print(f"1MB Document Indexing: {result}")
    
    @pytest.mark.slow
    @pytest.mark.memory_intensive
    def test_search_indexing_xlarge_document_10mb(self, perf_document_factory, 
                                                 perf_user, benchmark_timer,
                                                 performance_thresholds, memory_profiler):
        """Test search indexing performance for 10MB document with memory profiling."""
        
        def create_and_index_document():
            doc = perf_document_factory(
                title="Extra Large Document Performance Test",
                size_mb=10,
                created_by=perf_user
            )
            doc.update_search_vector()
            return doc
        
        # Benchmark with memory profiling
        with memory_profiler.profile_memory("search_indexing_10mb") as memory_result:
            result = benchmark_timer.benchmark_function(
                create_and_index_document,
                iterations=10,
                name="search_indexing_10mb",
                document_size="10MB"
            )
        
        # Assert performance thresholds
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['search_indexing_10mb'],
            max_percentile_95=performance_thresholds['search_indexing_10mb'] * 2
        )
        
        # Assert memory usage is reasonable
        assert memory_result['peak_memory_mb'] < performance_thresholds['memory_10mb_doc'], \
            f"Memory usage {memory_result['peak_memory_mb']:.2f}MB exceeds threshold"
        
        print(f"10MB Document Indexing: {result}")
        print(f"Memory Usage: Peak {memory_result['peak_memory_mb']:.2f}MB, "
              f"Delta {memory_result['memory_delta_mb']:.2f}MB")


@pytest.mark.performance
class TestBulkSearchIndexing:
    """Test bulk search indexing performance."""
    
    def test_bulk_indexing_100_documents(self, bulk_document_factory, 
                                        benchmark_timer, performance_thresholds):
        """Test bulk indexing of 100 documents."""
        
        def setup_documents():
            return bulk_document_factory(count=100, size_kb=5)
        
        def bulk_index_documents(documents):
            call_command('update_search_vectors', verbosity=0)
        
        result = benchmark_timer.benchmark_with_setup(
            setup_documents,
            bulk_index_documents,
            iterations=5,
            name="bulk_indexing_100_docs"
        )
        
        print(f"Bulk Indexing 100 Documents: {result}")
    
    @pytest.mark.slow
    def test_bulk_indexing_1000_documents(self, bulk_document_factory, 
                                         benchmark_timer, performance_thresholds,
                                         memory_profiler):
        """Test bulk indexing of 1000 documents with memory profiling."""
        
        def setup_documents():
            return bulk_document_factory(count=1000, size_kb=10)
        
        def bulk_index_documents(documents):
            call_command('update_search_vectors', verbosity=0)
        
        with memory_profiler.profile_memory("bulk_indexing_1000_docs") as memory_result:
            result = benchmark_timer.benchmark_with_setup(
                setup_documents,
                bulk_index_documents,
                iterations=3,
                name="bulk_indexing_1000_docs"
            )
        
        # Assert performance threshold
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['bulk_indexing_1000'],
            max_percentile_95=performance_thresholds['bulk_indexing_1000'] * 1.5
        )
        
        # Assert memory usage
        assert memory_result['peak_memory_mb'] < performance_thresholds['memory_bulk_1000_docs'], \
            f"Memory usage {memory_result['peak_memory_mb']:.2f}MB exceeds threshold"
        
        print(f"Bulk Indexing 1000 Documents: {result}")
        print(f"Memory Usage: Peak {memory_result['peak_memory_mb']:.2f}MB")


@pytest.mark.performance
class TestSearchQueryPerformance:
    """Test search query performance against various corpus sizes."""
    
    def test_search_query_small_corpus_100_docs(self, small_search_corpus, 
                                               perf_user, benchmark_timer):
        """Test search query performance against 100 documents."""
        query_generator = SearchQueryGenerator()
        queries = query_generator.generate_queries(10)
        
        def run_search_queries():
            for query in queries:
                results = DocumentService.search_documents(query, limit=50)
                # Consume the queryset to ensure database query execution
                list(results)
        
        result = benchmark_timer.benchmark_function(
            run_search_queries,
            iterations=20,
            name="search_query_100_docs",
            corpus_size="100 documents",
            query_count=len(queries)
        )
        
        print(f"Search Query Performance (100 docs): {result}")
    
    @pytest.mark.slow
    def test_search_query_medium_corpus_1000_docs(self, medium_search_corpus, 
                                                  perf_user, benchmark_timer,
                                                  performance_thresholds):
        """Test search query performance against 1000 documents."""
        query_generator = SearchQueryGenerator()
        queries = query_generator.generate_queries(20)
        
        def run_search_queries():
            for query in queries:
                results = DocumentService.search_documents(query, limit=50)
                # Consume the queryset
                list(results)
        
        result = benchmark_timer.benchmark_function(
            run_search_queries,
            iterations=10,
            name="search_query_1000_docs",
            corpus_size="1000 documents",
            query_count=len(queries)
        )
        
        # Performance should still be fast even with larger corpus
        single_query_time = result.mean_time / len(queries)
        assert single_query_time < performance_thresholds['search_query_large_corpus'], \
            f"Average query time {single_query_time:.4f}s exceeds threshold"
        
        print(f"Search Query Performance (1000 docs): {result}")
        print(f"Average time per query: {single_query_time:.4f}s")
    
    @pytest.mark.slow
    @pytest.mark.memory_intensive  
    def test_search_query_large_corpus_10000_docs(self, large_search_corpus, 
                                                  perf_user, benchmark_timer,
                                                  performance_thresholds, memory_profiler):
        """Test search query performance against 10000 documents with memory profiling."""
        query_generator = SearchQueryGenerator()
        queries = query_generator.generate_queries(50)
        
        def run_search_queries():
            for query in queries:
                results = DocumentService.search_documents(query, limit=50)
                # Consume the queryset
                list(results)
        
        with memory_profiler.profile_memory("search_query_large_corpus") as memory_result:
            result = benchmark_timer.benchmark_function(
                run_search_queries,
                iterations=5,
                name="search_query_10000_docs",
                corpus_size="10000 documents",
                query_count=len(queries)
            )
        
        # Performance assertions
        single_query_time = result.mean_time / len(queries)
        assert single_query_time < performance_thresholds['search_query_large_corpus'], \
            f"Average query time {single_query_time:.4f}s exceeds threshold"
        
        print(f"Search Query Performance (10k docs): {result}")
        print(f"Average time per query: {single_query_time:.4f}s")
        print(f"Memory Usage: Peak {memory_result['peak_memory_mb']:.2f}MB")


@pytest.mark.performance
class TestSearchVectorUpdates:
    """Test search vector update performance."""
    
    def test_search_vector_update_after_content_change(self, perf_document_factory,
                                                      perf_user, benchmark_timer,
                                                      performance_thresholds, content_generator):
        """Test search vector update performance after document content changes."""
        
        # Create a document to update
        doc = perf_document_factory(
            title="Document for Update Testing",
            size_kb=50,
            created_by=perf_user
        )
        
        def update_document_content():
            # Update content and trigger search vector update
            new_content = content_generator.generate_content(size_kb=60)
            doc.content = new_content
            doc.save()  # This should trigger search vector update
        
        result = benchmark_timer.benchmark_function(
            update_document_content,
            iterations=50,
            name="search_vector_update",
            document_size="50KB->60KB"
        )
        
        # Assert performance threshold
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['search_vector_update'],
            max_percentile_95=performance_thresholds['search_vector_update'] * 2
        )
        
        print(f"Search Vector Update Performance: {result}")
    
    def test_batch_search_vector_updates(self, bulk_document_factory, 
                                        benchmark_timer, content_generator):
        """Test batch search vector updates."""
        
        def setup_documents():
            return bulk_document_factory(count=50, size_kb=10)
        
        def batch_update_vectors(documents):
            new_content = content_generator.generate_content(size_kb=15)
            for doc in documents:
                doc.content = new_content
                doc.save()
        
        result = benchmark_timer.benchmark_with_setup(
            setup_documents,
            batch_update_vectors,
            iterations=5,
            name="batch_search_vector_update"
        )
        
        print(f"Batch Search Vector Update (50 docs): {result}")


@pytest.mark.performance
class TestSearchPerformanceRegressions:
    """Test for search performance regressions."""
    
    def test_search_performance_baseline(self, medium_search_corpus, benchmark_timer):
        """Establish baseline search performance metrics."""
        query_generator = SearchQueryGenerator()
        
        # Test various query types
        test_cases = [
            ("single_word_queries", query_generator.generate_queries(10)),
            ("phrase_queries", [f'"{q}"' for q in query_generator.generate_queries(5)]),
            ("compound_queries", [f"{q1} {q2}" for q1, q2 in 
                                zip(query_generator.generate_queries(5), 
                                    query_generator.generate_queries(5))])
        ]
        
        baseline_results = {}
        
        for test_name, queries in test_cases:
            def run_queries():
                for query in queries:
                    results = DocumentService.search_documents(query, limit=20)
                    list(results)  # Consume queryset
            
            result = benchmark_timer.benchmark_function(
                run_queries,
                iterations=10,
                name=f"baseline_{test_name}",
                query_count=len(queries)
            )
            
            baseline_results[test_name] = result
            print(f"Baseline {test_name}: {result}")
        
        # Save baseline results for future comparison
        benchmark_timer.save_results(
            f"performance_tests/reports/search_baseline_{int(time.time())}.json"
        )
        
        return baseline_results


@pytest.mark.performance
class TestSearchScalability:
    """Test search scalability with increasing data sizes."""
    
    @pytest.mark.slow
    @pytest.mark.memory_intensive
    def test_search_scalability_increasing_corpus_size(self, perf_user, bulk_document_factory,
                                                      benchmark_timer):
        """Test how search performance scales with increasing corpus size."""
        query_generator = SearchQueryGenerator()
        test_query = "performance test document"
        
        corpus_sizes = [100, 500, 1000, 2000]
        scalability_results = {}
        
        for size in corpus_sizes:
            # Create corpus of specified size
            corpus = bulk_document_factory(count=size, size_kb=5)
            
            def search_corpus():
                results = DocumentService.search_documents(test_query, limit=50)
                return list(results)
            
            result = benchmark_timer.benchmark_function(
                search_corpus,
                iterations=20,
                name=f"search_scalability_{size}_docs",
                corpus_size=size
            )
            
            scalability_results[size] = result
            print(f"Search Performance with {size} documents: {result}")
            
            # Clean up to avoid memory issues
            Document.objects.filter(id__in=[doc.id for doc in corpus]).delete()
        
        # Analyze scalability trend
        sizes = list(scalability_results.keys())
        times = [scalability_results[size].mean_time for size in sizes]
        
        # Calculate scaling factor (should be roughly logarithmic for good performance)
        scaling_factor = (times[-1] / times[0]) / (sizes[-1] / sizes[0])
        
        print(f"Scaling factor: {scaling_factor:.3f} (lower is better)")
        print("Search performance scaling analysis:")
        for size in sizes:
            result = scalability_results[size]
            print(f"  {size:4d} docs: {result.mean_time:.4f}s mean, "
                  f"{result.operations_per_second:.2f} ops/sec")
        
        # Assert that scaling is reasonable (not linear)
        assert scaling_factor < 0.5, f"Poor scaling detected: {scaling_factor:.3f}"
        
        return scalability_results
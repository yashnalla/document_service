"""
Large document performance tests for the document service.

This module contains comprehensive performance tests for handling large documents,
including creation, updates, search indexing, and memory usage validation.
"""

import pytest
import time
import gc
from typing import List, Dict, Any
from documents.models import Document
from documents.services import DocumentService
from .utils.benchmarks import PerformanceBenchmark
from .utils.profiling import MemoryProfiler, ResourceProfiler, garbage_collect_and_measure


@pytest.mark.performance
class TestLargeDocumentCreation:
    """Test performance of creating large documents."""
    
    def test_create_medium_document_1mb(self, perf_user, benchmark_timer, 
                                       performance_thresholds, content_generator):
        """Test creating 1MB documents."""
        
        def create_large_document():
            content = content_generator.generate_content(size_mb=1, content_type="mixed")
            return DocumentService.create_document(
                title="Large Document Test 1MB",
                content_text=content,
                user=perf_user
            )
        
        result = benchmark_timer.benchmark_function(
            create_large_document,
            iterations=20,
            name="create_document_1mb",
            document_size="1MB"
        )
        
        # Keep documents in database for analysis
        
        print(f"1MB Document Creation: {result}")
    
    @pytest.mark.slow
    def test_create_large_document_10mb(self, perf_user, benchmark_timer, 
                                       performance_thresholds, content_generator,
                                       memory_profiler):
        """Test creating 10MB documents with memory profiling."""
        
        def create_large_document():
            content = content_generator.generate_content(size_mb=10, content_type="mixed")
            return DocumentService.create_document(
                title="Large Document Test 10MB",
                content_text=content,
                user=perf_user
            )
        
        with memory_profiler.profile_memory("create_document_10mb") as memory_result:
            result = benchmark_timer.benchmark_function(
                create_large_document,
                iterations=10,
                name="create_document_10mb",
                document_size="10MB"
            )
        
        # Assert performance thresholds
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['large_doc_creation_10mb'],
            max_percentile_95=performance_thresholds['large_doc_creation_10mb'] * 2
        )
        
        # Assert memory usage
        assert memory_result['peak_memory_mb'] < performance_thresholds['memory_10mb_doc'], \
            f"Memory usage {memory_result['peak_memory_mb']:.2f}MB exceeds threshold"
        
        # Keep documents in database for analysis
        
        print(f"10MB Document Creation: {result}")
        print(f"Memory Usage: Peak {memory_result['peak_memory_mb']:.2f}MB, "
              f"Delta {memory_result['memory_delta_mb']:.2f}MB")


@pytest.mark.performance
class TestLargeDocumentOperations:
    """Test various operations on large documents."""
    
    def test_large_document_save_load_10mb(self, perf_document_factory, perf_user,
                                          benchmark_timer, performance_thresholds):
        """Test save/load performance for 10MB documents."""
        
        # Create a large document once
        large_doc = perf_document_factory(
            title="Large Document Save/Load Test",
            size_mb=10,
            created_by=perf_user
        )
        
        def save_and_reload_document():
            # Modify and save
            large_doc.title = f"Modified {time.time()}"
            large_doc.save()
            
            # Reload from database
            reloaded_doc = Document.objects.get(id=large_doc.id)
            return reloaded_doc
        
        result = benchmark_timer.benchmark_function(
            save_and_reload_document,
            iterations=20,
            name="save_load_10mb_document",
            document_size="10MB"
        )
        
        # Assert performance threshold
        benchmark_timer.assert_performance_threshold(
            result,
            max_mean_time=performance_thresholds['large_doc_save_load_10mb'],
            max_percentile_95=performance_thresholds['large_doc_save_load_10mb'] * 2
        )
        
        print(f"10MB Document Save/Load: {result}")
    
    def test_large_document_content_update_10mb(self, perf_document_factory, perf_user,
                                               benchmark_timer, content_generator):
        """Test content update performance for large documents."""
        
        # Create initial document
        large_doc = perf_document_factory(
            title="Large Document Update Test",
            size_mb=10,
            created_by=perf_user
        )
        
        def update_document_content():
            # Generate new content
            new_content = content_generator.generate_content(size_mb=10, content_type="code")
            
            # Update using DocumentService
            return DocumentService.update_document(
                document=large_doc,
                title="Updated Large Document",
                content_text=new_content,
                user=perf_user
            )
        
        result = benchmark_timer.benchmark_function(
            update_document_content,
            iterations=10,
            name="update_10mb_document_content",
            document_size="10MB"
        )
        
        print(f"10MB Document Content Update: {result}")
    
    def test_large_document_version_control(self, perf_document_factory, perf_user,
                                           benchmark_timer, content_generator):
        """Test version control performance with large documents."""
        
        large_doc = perf_document_factory(
            title="Large Document Version Test",
            size_mb=5,
            created_by=perf_user
        )
        
        def create_document_version():
            # Create a new version by updating content
            new_content = content_generator.generate_content(size_kb=5120)  # 5MB
            large_doc.content = new_content
            large_doc.increment_version()
            return large_doc.version
        
        result = benchmark_timer.benchmark_function(
            create_document_version,
            iterations=15,
            name="large_document_versioning",
            document_size="5MB"
        )
        
        print(f"Large Document Versioning: {result}")
        print(f"Final version: {large_doc.version}")


@pytest.mark.performance
class TestLargeDocumentScalability:
    """Test scalability characteristics with large documents."""
    
    @pytest.mark.slow
    @pytest.mark.memory_intensive
    def test_document_size_scalability(self, perf_user, benchmark_timer, content_generator):
        """Test how performance scales with document size."""
        
        document_sizes = [1, 5, 10, 25]  # MB
        scalability_results = {}
        
        for size_mb in document_sizes:
            def create_document_of_size():
                content = content_generator.generate_content(size_mb=size_mb)
                doc = DocumentService.create_document(
                    title=f"Scalability Test {size_mb}MB",
                    content_text=content,
                    user=perf_user
                )
                # Keep document in database
                return doc
            
            result = benchmark_timer.benchmark_function(
                create_document_of_size,
                iterations=10 if size_mb <= 10 else 5,  # Fewer iterations for larger docs
                name=f"create_document_{size_mb}mb",
                document_size=f"{size_mb}MB"
            )
            
            scalability_results[size_mb] = result
            print(f"Document Creation Performance ({size_mb}MB): {result}")
        
        # Analyze scaling characteristics
        sizes = list(scalability_results.keys())
        times = [scalability_results[size].mean_time for size in sizes]
        
        print("\nDocument Size Scalability Analysis:")
        for i, size in enumerate(sizes):
            result = scalability_results[size]
            if i > 0:
                size_ratio = size / sizes[0]
                time_ratio = result.mean_time / times[0]
                efficiency = size_ratio / time_ratio
                print(f"  {size:2d}MB: {result.mean_time:.3f}s (efficiency: {efficiency:.2f})")
            else:
                print(f"  {size:2d}MB: {result.mean_time:.3f}s (baseline)")
        
        return scalability_results
    
    def test_concurrent_large_document_simulation(self, perf_user, benchmark_timer,
                                                 content_generator, memory_profiler):
        """Simulate concurrent operations on large documents."""
        
        # Create a large document to work with
        large_content = content_generator.generate_content(size_mb=15)
        doc = DocumentService.create_document(
            title="Concurrent Operations Test Document",
            content_text=large_content,
            user=perf_user
        )
        
        def simulate_concurrent_operations():
            # Simulate operations that might happen concurrently
            
            # 1. Read the document
            loaded_doc = Document.objects.get(id=doc.id)
            
            # 2. Update search vector
            loaded_doc.update_search_vector()
            
            # 3. Perform a search that might return this document  
            search_results = list(DocumentService.search_documents("concurrent", limit=10))
            
            # 4. Update document version
            loaded_doc.increment_version()
            
            return len(search_results)
        
        with memory_profiler.profile_memory("concurrent_operations") as memory_result:
            result = benchmark_timer.benchmark_function(
                simulate_concurrent_operations,
                iterations=15,
                name="concurrent_large_document_ops",
                document_size="15MB"
            )
        
        # Keep document in database for analysis
        
        print(f"Concurrent Large Document Operations: {result}")
        print(f"Memory Usage: Peak {memory_result['peak_memory_mb']:.2f}MB")
        
        return result
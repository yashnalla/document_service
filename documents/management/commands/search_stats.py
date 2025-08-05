"""
Management command to display search index statistics and test search performance.

This command provides insights into:
- Search index health and coverage
- Document statistics
- Sample search performance metrics
- Search functionality testing
"""

from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import connection
from documents.models import Document
from documents.services import DocumentService
from django.contrib.auth.models import User
import time
import random


class Command(BaseCommand):
    help = 'Display search index statistics and performance metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-search',
            action='store_true',
            help='Run sample search performance tests',
        )
        parser.add_argument(
            '--sample-queries',
            nargs='+',
            default=['document', 'test', 'content', 'example'],
            help='Sample search queries to test (space-separated)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed statistics and queries',
        )

    def handle(self, *args, **options):
        test_search = options['test_search']
        sample_queries = options['sample_queries']
        verbose = options['verbose']

        self.stdout.write(
            self.style.SUCCESS('🔍 Document Search Statistics')
        )
        self.stdout.write('=' * 50)

        # Basic document statistics
        self.show_document_stats(verbose)

        # Search index statistics
        self.show_search_index_stats(verbose)

        # Database index information
        if verbose:
            self.show_database_index_info()

        # Performance testing
        if test_search:
            self.stdout.write('')
            self.run_search_performance_tests(sample_queries, verbose)

        # Usage recommendations
        self.show_recommendations()

    def show_document_stats(self, verbose=False):
        """Display basic document statistics."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('📊 Document Statistics'))
        self.stdout.write('-' * 30)

        total_docs = Document.objects.count()
        docs_with_search_vector = Document.objects.filter(
            search_vector__isnull=False
        ).count()
        docs_without_search_vector = total_docs - docs_with_search_vector

        self.stdout.write(f'Total documents: {total_docs}')
        self.stdout.write(f'Documents with search vectors: {docs_with_search_vector}')
        
        if docs_without_search_vector > 0:
            self.stdout.write(
                self.style.ERROR(
                    f'Documents without search vectors: {docs_without_search_vector}'
                )
            )
            self.stdout.write(
                '  Run: python manage.py update_search_vectors'
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ All documents have search vectors')
            )

        # Content statistics
        if verbose and total_docs > 0:
            self.stdout.write('')
            self.show_content_statistics()

    def show_content_statistics(self):
        """Show detailed content statistics."""
        self.stdout.write('Content Analysis:')
        
        # Sample documents for analysis
        sample_size = min(100, Document.objects.count())
        documents = Document.objects.all()[:sample_size]
        
        total_content_length = 0
        total_title_length = 0
        empty_content_count = 0
        
        for doc in documents:
            plain_text = doc.content or ""
            title_length = len(doc.title)
            content_length = len(plain_text)
            
            total_title_length += title_length
            total_content_length += content_length
            
            if content_length == 0:
                empty_content_count += 1

        if sample_size > 0:
            avg_title_length = total_title_length / sample_size
            avg_content_length = total_content_length / sample_size
            
            self.stdout.write(f'  Average title length: {avg_title_length:.1f} characters')
            self.stdout.write(f'  Average content length: {avg_content_length:.1f} characters')
            self.stdout.write(f'  Empty content documents: {empty_content_count}')
            
            if sample_size < Document.objects.count():
                self.stdout.write(f'  (Analysis based on {sample_size} sample documents)')

    def show_search_index_stats(self, verbose=False):
        """Display search index statistics."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('🗂️  Search Index Statistics'))
        self.stdout.write('-' * 35)

        # Check if PostgreSQL search extensions are available
        try:
            with connection.cursor() as cursor:
                # Check for text search configuration
                cursor.execute("""
                    SELECT cfgname, cfgparser, cfgowner 
                    FROM pg_ts_config 
                    WHERE cfgname = 'english'
                """)
                config_info = cursor.fetchone()
                
                if config_info:
                    self.stdout.write('✓ PostgreSQL text search configuration: english')
                else:
                    self.stdout.write('⚠ English text search configuration not found')

                # Check GIN index
                cursor.execute("""
                    SELECT indexname, tablename, indexdef
                    FROM pg_indexes 
                    WHERE tablename = 'documents_document' 
                    AND indexdef LIKE '%gin%'
                """)
                gin_indexes = cursor.fetchall()
                
                if gin_indexes:
                    self.stdout.write(f'✓ GIN indexes found: {len(gin_indexes)}')
                    if verbose:
                        for index in gin_indexes:
                            self.stdout.write(f'  - {index[0]}')
                else:
                    self.stdout.write(
                        self.style.ERROR('✗ No GIN indexes found for search')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error checking database indexes: {str(e)}')
            )

    def show_database_index_info(self):
        """Show detailed database index information."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('🗄️  Database Index Details'))
        self.stdout.write('-' * 35)

        try:
            with connection.cursor() as cursor:
                # Get detailed index information
                cursor.execute("""
                    SELECT 
                        i.relname as index_name,
                        t.relname as table_name,
                        a.attname as column_name,
                        am.amname as index_type,
                        pg_size_pretty(pg_relation_size(i.oid)) as index_size
                    FROM pg_class i
                    JOIN pg_index ix ON i.oid = ix.indexrelid
                    JOIN pg_class t ON ix.indrelid = t.oid
                    JOIN pg_am am ON i.relam = am.oid
                    LEFT JOIN pg_attribute a ON t.oid = a.attrelid AND a.attnum = ANY(ix.indkey)
                    WHERE t.relname = 'documents_document'
                    AND i.relname LIKE '%search%'
                    ORDER BY i.relname;
                """)
                
                index_info = cursor.fetchall()
                
                if index_info:
                    for info in index_info:
                        self.stdout.write(
                            f'Index: {info[0]} ({info[3]}) - Size: {info[4]}'
                        )
                else:
                    self.stdout.write('No search-related indexes found')

        except Exception as e:
            self.stdout.write(f'Could not retrieve index details: {str(e)}')

    def run_search_performance_tests(self, sample_queries, verbose=False):
        """Run search performance tests with sample queries."""
        self.stdout.write(self.style.HTTP_INFO('⚡ Search Performance Tests'))
        self.stdout.write('-' * 35)

        # Get a test user
        test_user = User.objects.first()
        if not test_user:
            self.stdout.write(
                self.style.WARNING('No users found - creating test user for search tests')
            )
            test_user = User.objects.create_user(
                username='test_search_user',
                email='test@example.com'
            )

        total_time = 0
        successful_searches = 0

        for query in sample_queries:
            try:
                start_time = time.time()
                
                # Test DocumentService search
                results = DocumentService.search_documents(
                    query=query,
                    user=test_user,
                    limit=10
                )
                
                end_time = time.time()
                search_time = end_time - start_time
                total_time += search_time
                successful_searches += 1

                result_count = results['total_results']
                
                self.stdout.write(
                    f'Query: "{query}" → {result_count} results in {search_time*1000:.2f}ms'
                )
                
                if verbose and result_count > 0:
                    # Show top results
                    for doc in list(results['documents'])[:3]:
                        title = doc.title[:50] + '...' if len(doc.title) > 50 else doc.title
                        self.stdout.write(f'  - {title}')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Query "{query}" failed: {str(e)}')
                )

        # Performance summary
        if successful_searches > 0:
            avg_time = total_time / successful_searches
            self.stdout.write('')
            self.stdout.write(f'Performance Summary:')
            self.stdout.write(f'  Successful searches: {successful_searches}/{len(sample_queries)}')
            self.stdout.write(f'  Average search time: {avg_time*1000:.2f}ms')
            self.stdout.write(f'  Total test time: {total_time*1000:.2f}ms')
            
            # Performance assessment
            if avg_time < 0.1:  # Less than 100ms
                self.stdout.write(
                    self.style.SUCCESS('✓ Excellent search performance!')
                )
            elif avg_time < 0.5:  # Less than 500ms
                self.stdout.write(
                    self.style.SUCCESS('✓ Good search performance')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ Search performance could be improved')
                )

    def show_recommendations(self):
        """Show recommendations for search optimization."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('💡 Recommendations'))
        self.stdout.write('-' * 25)

        docs_without_vectors = Document.objects.filter(
            search_vector__isnull=True
        ).count()

        if docs_without_vectors > 0:
            self.stdout.write(
                '• Run search vector update: python manage.py update_search_vectors'
            )

        self.stdout.write('• Test search in web interface: /documents/')
        self.stdout.write('• Monitor search performance in production')
        self.stdout.write('• Consider search result caching for frequently used queries')
        
        # Check document count for recommendations
        total_docs = Document.objects.count()
        if total_docs > 10000:
            self.stdout.write('• Consider search result pagination for large datasets')
        
        if total_docs > 100000:
            self.stdout.write('• Consider implementing search result caching')
            self.stdout.write('• Monitor PostgreSQL performance and tune as needed')

        self.stdout.write('')
        self.stdout.write('📚 For more information, see the search documentation in CLAUDE.md')
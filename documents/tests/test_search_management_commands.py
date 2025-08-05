"""
Tests for search-related management commands.

This test module covers:
- update_search_vectors management command
- search_stats management command
"""

import pytest
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVector
from io import StringIO
from documents.models import Document
from documents.services import DocumentService


class UpdateSearchVectorsCommandTestCase(TestCase):
    """Test the update_search_vectors management command."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create documents without search vectors (simulate old documents)
        self.doc1 = Document.objects.create(
            title='Test Document 1',
            content={
                'root': {
                    'children': [
                        {
                            'type': 'paragraph',
                            'children': [
                                {'type': 'text', 'text': 'Content for document 1'}
                            ]
                        }
                    ]
                }
            },
            created_by=self.user
        )
        
        self.doc2 = Document.objects.create(
            title='Test Document 2',
            content={
                'root': {
                    'children': [
                        {
                            'type': 'paragraph',
                            'children': [
                                {'type': 'text', 'text': 'Content for document 2'}
                            ]
                        }
                    ]
                }
            },
            created_by=self.user
        )
        
        # Ensure they don't have search vectors initially
        Document.objects.filter(
            id__in=[self.doc1.id, self.doc2.id]
        ).update(search_vector=None)
    
    def test_update_search_vectors_basic_functionality(self):
        """Test basic update_search_vectors command functionality."""
        # Verify documents don't have search vectors
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()
        self.assertIsNone(self.doc1.search_vector)
        self.assertIsNone(self.doc2.search_vector)
        
        # Run command
        out = StringIO()
        call_command('update_search_vectors', stdout=out)
        
        # Verify search vectors were created
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()
        self.assertIsNotNone(self.doc1.search_vector)
        self.assertIsNotNone(self.doc2.search_vector)
        
        # Check command output
        output = out.getvalue()
        self.assertIn('Found 2 documents to process', output)
        self.assertIn('Successfully processed: 2', output)
    
    def test_update_search_vectors_with_existing_vectors(self):
        """Test command behavior when search vectors already exist."""
        # First run to create search vectors
        call_command('update_search_vectors', verbosity=0)
        
        # Second run should find no documents to process
        out = StringIO()
        call_command('update_search_vectors', stdout=out)
        
        output = out.getvalue()
        self.assertIn('All documents already have search vectors', output)
    
    def test_update_search_vectors_force_flag(self):
        """Test --force flag to rebuild all search vectors."""
        # First run to create search vectors
        call_command('update_search_vectors', verbosity=0)
        
        # Run with --force should process all documents
        out = StringIO()
        call_command('update_search_vectors', '--force', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Found 2 documents to process', output)
        self.assertIn('Successfully processed: 2', output)
    
    def test_update_search_vectors_specific_document(self):
        """Test updating search vector for a specific document."""
        out = StringIO()
        call_command(
            'update_search_vectors', 
            f'--document-id={self.doc1.id}', 
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn(f'Processing document: {self.doc1.title}', output)
        self.assertIn('Updated search vector', output)
        
        # Only doc1 should have search vector
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()
        self.assertIsNotNone(self.doc1.search_vector)
        self.assertIsNone(self.doc2.search_vector)
    
    def test_update_search_vectors_nonexistent_document(self):
        """Test command with nonexistent document ID."""
        from django.core.management.base import CommandError
        import uuid
        
        fake_id = str(uuid.uuid4())
        
        with self.assertRaises(CommandError):
            call_command('update_search_vectors', f'--document-id={fake_id}')
    
    def test_update_search_vectors_dry_run(self):
        """Test --dry-run flag."""
        out = StringIO()
        call_command('update_search_vectors', '--dry-run', stdout=out)
        
        output = out.getvalue()
        self.assertIn('DRY RUN MODE', output)
        self.assertIn('Would update 2 documents', output)
        
        # Search vectors should not be created
        self.doc1.refresh_from_db()
        self.doc2.refresh_from_db()
        self.assertIsNone(self.doc1.search_vector)
        self.assertIsNone(self.doc2.search_vector)
    
    def test_update_search_vectors_batch_size(self):
        """Test --batch-size parameter."""
        # Create more documents 
        for i in range(5):
            Document.objects.create(
                title=f'Batch Test Doc {i}',
                content='Test content',
                created_by=self.user
            )
        
        out = StringIO()
        # Use --force to update all documents regardless of search vector status
        call_command('update_search_vectors', '--batch-size=3', '--force', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Found 7 documents to process', output)  # 2 original + 5 new
        self.assertIn('Processing documents in batches of 3', output)
    
    def test_update_search_vectors_error_handling(self):
        """Test command error handling with malformed content."""
        # Create document with potentially problematic content
        bad_doc = Document.objects.create(
            title='Bad Document',
            content={'malformed': 'structure'},
            created_by=self.user
        )
        
        # Command should handle errors gracefully
        out = StringIO()
        call_command('update_search_vectors', stdout=out)
        
        # Should complete successfully even with some errors
        output = out.getvalue()
        self.assertIn('Search vector update completed', output)


class SearchStatsCommandTestCase(TestCase):
    """Test the search_stats management command."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test documents with search vectors
        self.doc1 = DocumentService.create_document(
            title='Django Tutorial',
            content_text='Learn Django web development with this comprehensive guide',
            user=self.user
        )
        
        self.doc2 = DocumentService.create_document(
            title='Python Basics',
            content_text='Introduction to Python programming language fundamentals',
            user=self.user
        )
        
        # Ensure search vectors are populated
        call_command('update_search_vectors', verbosity=0)
    
    def test_search_stats_basic_functionality(self):
        """Test basic search_stats command functionality."""
        out = StringIO()
        call_command('search_stats', stdout=out)
        
        output = out.getvalue()
        
        # Check for main sections
        self.assertIn('Document Search Statistics', output)
        self.assertIn('Document Statistics', output)
        self.assertIn('Search Index Statistics', output)
        self.assertIn('Recommendations', output)
        
        # Check document counts
        self.assertIn('Total documents: 2', output)
        self.assertIn('Documents with search vectors: 2', output)
        self.assertIn('All documents have search vectors', output)
    
    def test_search_stats_with_missing_search_vectors(self):
        """Test search_stats when some documents lack search vectors."""
        # Remove search vector from one document
        Document.objects.filter(id=self.doc1.id).update(search_vector=None)
        
        out = StringIO()
        call_command('search_stats', stdout=out)
        
        output = out.getvalue()
        # Should show 1 document without search vectors (out of 2 total)
        self.assertIn('Documents without search vectors: 1', output)
        self.assertIn('Documents with search vectors: 1', output)
        self.assertIn('Run: python manage.py update_search_vectors', output)
    
    def test_search_stats_verbose_mode(self):
        """Test search_stats with --verbose flag."""
        out = StringIO()
        call_command('search_stats', '--verbose', stdout=out)
        
        output = out.getvalue()
        
        # Should include additional information
        self.assertIn('Content Analysis:', output)
        self.assertIn('Average title length:', output)
        self.assertIn('Average content length:', output)
        self.assertIn('Database Index Details', output)
    
    def test_search_stats_with_performance_tests(self):
        """Test search_stats with --test-search flag."""
        out = StringIO()
        call_command('search_stats', '--test-search', stdout=out)
        
        output = out.getvalue()
        
        # Should include performance testing section
        self.assertIn('Search Performance Tests', output)
        self.assertIn('Performance Summary:', output)
        self.assertIn('Average search time:', output)
        
        # Should test default queries
        self.assertIn('Query: "document"', output)
        self.assertIn('Query: "test"', output)
        self.assertIn('Query: "content"', output)
        self.assertIn('Query: "example"', output)
    
    def test_search_stats_custom_sample_queries(self):
        """Test search_stats with custom sample queries."""
        out = StringIO()
        call_command(
            'search_stats', 
            '--test-search',
            '--sample-queries', 'Django', 'Python',
            stdout=out
        )
        
        output = out.getvalue()
        
        # Should test custom queries
        self.assertIn('Query: "Django"', output)
        self.assertIn('Query: "Python"', output)
        
        # Should not test default queries
        self.assertNotIn('Query: "document"', output)
        self.assertNotIn('Query: "test"', output)
    
    def test_search_stats_database_index_information(self):
        """Test that search_stats shows database index information."""
        out = StringIO()
        call_command('search_stats', '--verbose', stdout=out)
        
        output = out.getvalue()
        
        # Should show PostgreSQL configuration
        self.assertIn('PostgreSQL text search configuration', output)
        self.assertIn('GIN indexes found', output)
    
    def test_search_stats_performance_assessment(self):
        """Test performance assessment in search_stats."""
        out = StringIO()
        call_command('search_stats', '--test-search', stdout=out)
        
        output = out.getvalue()
        
        # Should provide performance assessment
        self.assertTrue(
            'Excellent search performance' in output or
            'Good search performance' in output or
            'Search performance could be improved' in output
        )
    
    def test_search_stats_recommendations(self):
        """Test that search_stats provides helpful recommendations."""
        out = StringIO()
        call_command('search_stats', stdout=out)
        
        output = out.getvalue()
        
        # Should include recommendations
        self.assertIn('Test search in web interface', output)
        self.assertIn('Monitor search performance', output)
        self.assertIn('search documentation in CLAUDE.md', output)
    
    def test_search_stats_with_no_users(self):
        """Test search_stats behavior when no users exist for testing."""
        # Delete all users
        User.objects.all().delete()
        
        out = StringIO()
        call_command('search_stats', '--test-search', stdout=out)
        
        output = out.getvalue()
        
        # Should handle gracefully and create test user
        self.assertIn('No users found - creating test user', output)
    
    def test_search_stats_error_handling(self):
        """Test search_stats error handling."""
        # This test ensures the command doesn't crash on unexpected errors
        out = StringIO()
        err = StringIO()
        
        try:
            call_command('search_stats', stdout=out, stderr=err)
            # Should complete without exceptions
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"search_stats command raised an exception: {e}")


@pytest.mark.django_db
class SearchManagementIntegrationTestCase:
    """Integration tests for search management commands."""
    
    def test_command_workflow_integration(self):
        """Test complete workflow using management commands."""
        # Create user and documents
        user = User.objects.create_user(
            username='workflow_user',
            email='workflow@example.com',
            password='testpass123'
        )
        
        # Create documents without search vectors
        doc1 = Document.objects.create(
            title='Workflow Test Doc 1',
            content={
                'root': {
                    'children': [
                        {
                            'type': 'paragraph',
                            'children': [
                                {'type': 'text', 'text': 'Testing workflow integration'}
                            ]
                        }
                    ]
                }
            },
            created_by=user
        )
        
        # Clear search vector
        Document.objects.filter(id=doc1.id).update(search_vector=None)
        
        # 1. Check stats shows missing search vectors
        out1 = StringIO()
        call_command('search_stats', stdout=out1)
        output1 = out1.getvalue()
        assert 'Documents without search vectors: 1' in output1
        
        # 2. Update search vectors
        out2 = StringIO()
        call_command('update_search_vectors', stdout=out2)
        output2 = out2.getvalue()
        assert 'Successfully processed: 1' in output2
        
        # 3. Check stats shows all vectors present
        out3 = StringIO()
        call_command('search_stats', stdout=out3)
        output3 = out3.getvalue()
        assert 'All documents have search vectors' in output3
        
        # 4. Test search performance
        out4 = StringIO()
        call_command('search_stats', '--test-search', stdout=out4)
        output4 = out4.getvalue()
        assert 'Performance Summary:' in output4
    
    def test_makefile_commands_integration(self):
        """Test that Makefile commands work correctly (simulated)."""
        # This would be tested in actual deployment, but we can test
        # the underlying management commands that Makefile calls
        
        user = User.objects.create_user(
            username='makefile_user',
            email='makefile@example.com',
            password='testpass123'
        )
        
        # Simulate 'make search-stats'
        out_stats = StringIO()
        call_command('search_stats', stdout=out_stats)
        stats_output = out_stats.getvalue()
        assert 'Document Search Statistics' in stats_output
        
        # Simulate 'make search-reindex'
        out_reindex = StringIO()
        call_command('update_search_vectors', stdout=out_reindex)
        reindex_output = out_reindex.getvalue()
        assert 'Search vector update completed' in reindex_output
        
        # Simulate 'make search-test'
        out_test = StringIO()
        call_command('search_stats', '--test-search', '--verbose', stdout=out_test)
        test_output = out_test.getvalue()
        assert 'Search Performance Tests' in test_output
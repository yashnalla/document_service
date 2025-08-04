"""
Management command to rebuild search vectors for all documents.

This command is useful for:
- Initial population of search vectors after adding the search functionality
- Rebuilding search vectors after making changes to search logic
- Fixing search vectors for documents that may have become corrupted
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.postgres.search import SearchVector
from django.db import transaction
from documents.models import Document
import time


class Command(BaseCommand):
    help = 'Update search vectors for all documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of documents to process in each batch (default: 1000)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update search vectors even if they already exist',
        )
        parser.add_argument(
            '--document-id',
            type=str,
            help='Update search vector for a specific document ID only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        force = options['force']
        document_id = options['document_id']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Handle specific document
        if document_id:
            try:
                document = Document.objects.get(pk=document_id)
                self.update_single_document(document, dry_run)
                return
            except Document.DoesNotExist:
                raise CommandError(f'Document with ID "{document_id}" does not exist')

        # Handle all documents
        self.update_all_documents(batch_size, force, dry_run)

    def update_single_document(self, document, dry_run=False):
        """Update search vector for a single document."""
        self.stdout.write(f'Processing document: {document.title} ({document.id})')
        
        if dry_run:
            self.stdout.write('  [DRY RUN] Would update search vector')
            return

        try:
            content_text = document.get_plain_text()
            
            with transaction.atomic():
                Document.objects.filter(pk=document.pk).update(
                    search_vector=(
                        SearchVector('title', weight='A') +
                        SearchVector(models.Value(content_text), weight='B')
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Updated search vector')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Failed to update: {str(e)}')
            )

    def update_all_documents(self, batch_size, force, dry_run):
        """Update search vectors for all documents."""
        # Get documents that need updating
        if force:
            documents = Document.objects.all()
        else:
            documents = Document.objects.filter(search_vector__isnull=True)

        total_count = documents.count()
        
        if total_count == 0:
            if force:
                self.stdout.write(
                    self.style.WARNING('No documents found in the database')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        'All documents already have search vectors. '
                        'Use --force to rebuild all search vectors.'
                    )
                )
            return

        self.stdout.write(f'Found {total_count} documents to process')
        
        if dry_run:
            self.stdout.write(f'[DRY RUN] Would update {total_count} documents')
            return

        # Process in batches
        start_time = time.time()
        processed = 0
        errors = 0

        self.stdout.write(f'Processing documents in batches of {batch_size}...')

        for i in range(0, total_count, batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    for document in batch:
                        try:
                            content_text = document.get_plain_text()
                            
                            # Update the search vector
                            Document.objects.filter(pk=document.pk).update(
                                search_vector=(
                                    SearchVector('title', weight='A') +
                                    SearchVector(models.Value(content_text), weight='B')
                                )
                            )
                            processed += 1
                            
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Error processing document {document.id}: {str(e)}'
                                )
                            )
                            errors += 1

                # Progress update
                progress = min(i + batch_size, total_count)
                self.stdout.write(f'Processed {progress}/{total_count} documents...')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Batch processing error: {str(e)}')
                )
                errors += batch_size

        # Final results
        end_time = time.time()
        duration = end_time - start_time

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Search vector update completed!'))
        self.stdout.write(f'  Total documents: {total_count}')
        self.stdout.write(f'  Successfully processed: {processed}')
        if errors > 0:
            self.stdout.write(
                self.style.ERROR(f'  Errors: {errors}')
            )
        self.stdout.write(f'  Duration: {duration:.2f} seconds')
        
        if processed > 0:
            avg_time = duration / processed
            self.stdout.write(f'  Average time per document: {avg_time:.3f} seconds')

        # Provide next steps
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  • Test search functionality: python manage.py search_stats')
        self.stdout.write('  • Try searching in the web interface')
        
        if errors > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: {errors} documents had errors. '
                    'Check the error messages above and consider running the command again.'
                )
            )


# Fix import issue
from django.db import models
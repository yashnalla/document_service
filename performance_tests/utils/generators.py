"""
Test data generators for performance testing.

This module provides utilities to generate realistic document content
of various sizes and types for performance testing scenarios.
"""

import random
import string
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path


class DocumentContentGenerator:
    """Generator for realistic document content of various sizes."""
    
    # Sample content templates for different document types
    LOREM_IPSUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod 
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor 
in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur 
sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."""
    
    CODE_SAMPLES = [
        """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class DataProcessor:
    def __init__(self, data):
        self.data = data
        self.processed = False
    
    def process(self):
        if not self.processed:
            self.data = [x * 2 for x in self.data]
            self.processed = True
        return self.data
""",
        """
import React, { useState, useEffect } from 'react';

const DocumentEditor = ({ documentId }) => {
    const [content, setContent] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    
    useEffect(() => {
        fetchDocument(documentId).then(doc => {
            setContent(doc.content);
            setIsLoading(false);
        });
    }, [documentId]);
    
    const handleSave = async () => {
        await saveDocument(documentId, content);
    };
    
    return (
        <div className="editor">
            {isLoading ? (
                <div>Loading...</div>
            ) : (
                <textarea 
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                />
            )}
            <button onClick={handleSave}>Save</button>
        </div>
    );
};
""",
        """
public class DocumentService {
    private final DocumentRepository repository;
    private final SearchService searchService;
    
    public DocumentService(DocumentRepository repository, SearchService searchService) {
        this.repository = repository;
        this.searchService = searchService;
    }
    
    @Transactional
    public Document createDocument(String title, String content, User author) {
        Document document = new Document();
        document.setTitle(title);
        document.setContent(content);
        document.setAuthor(author);
        document.setCreatedAt(Instant.now());
        
        Document saved = repository.save(document);
        searchService.indexDocument(saved);
        
        return saved;
    }
    
    public List<Document> searchDocuments(String query, int limit) {
        return searchService.search(query, limit);
    }
}
"""
    ]
    
    STRUCTURED_CONTENT_TEMPLATES = [
        """# Technical Documentation

## Overview
This document provides comprehensive information about the system architecture
and implementation details.

## Architecture
The system follows a microservices architecture with the following components:

### Core Services
- **API Gateway**: Routes requests to appropriate services
- **Authentication Service**: Handles user authentication and authorization
- **Document Service**: Manages document creation, editing, and storage
- **Search Service**: Provides full-text search capabilities

### Data Layer
- **PostgreSQL**: Primary database for structured data
- **Redis**: Caching layer and session storage
- **Elasticsearch**: Search index and analytics

## Implementation Details
The implementation uses modern technologies and follows best practices:

```python
class DocumentProcessor:
    def __init__(self, config):
        self.config = config
        self.cache = Redis(host=config.redis_host)
    
    def process_document(self, document):
        # Processing logic here
        return processed_document
```

## Performance Considerations
- All operations are optimized for sub-100ms response times
- Database queries use appropriate indexes
- Caching is implemented at multiple layers
- Search operations leverage full-text search capabilities

## Monitoring and Observability
The system includes comprehensive monitoring:
- Application metrics via Prometheus
- Distributed tracing with Jaeger
- Centralized logging with ELK stack
- Health checks and alerting
""",
        """# Project Requirements Document

## Executive Summary
This project aims to develop a modern document management system with 
collaborative editing capabilities and advanced search functionality.

## Functional Requirements

### Document Management
- Users can create, edit, and delete documents
- Support for real-time collaborative editing
- Version control and change tracking
- Document organization with folders and tags

### Search Functionality
- Full-text search across all documents
- Advanced filtering and sorting options
- Search result highlighting and snippets
- Search analytics and suggestions

### User Management
- User registration and authentication
- Role-based access control
- User profiles and preferences
- Activity tracking and audit logs

## Technical Requirements

### Performance
- Page load times under 2 seconds
- Search results in under 100ms
- Support for documents up to 100MB
- Concurrent users up to 10,000

### Scalability
- Horizontal scaling capabilities
- Database partitioning support
- CDN integration for static assets
- Auto-scaling based on load

### Security
- HTTPS encryption for all communications
- Input validation and sanitization
- SQL injection prevention
- XSS protection mechanisms

## Implementation Timeline
- Phase 1: Core document management (4 weeks)
- Phase 2: Search functionality (3 weeks)
- Phase 3: Collaborative editing (4 weeks)
- Phase 4: Performance optimization (2 weeks)

## Success Metrics
- User adoption rate > 80%
- Average document processing time < 500ms
- System uptime > 99.9%
- User satisfaction score > 4.5/5
"""
    ]
    
    def __init__(self):
        """Initialize the content generator."""
        self.random = random.Random()
        
    def generate_content(self, size_kb: Optional[int] = None, size_mb: Optional[int] = None, 
                        content_type: str = "mixed") -> str:
        """
        Generate document content of specified size.
        
        Args:
            size_kb: Target size in kilobytes
            size_mb: Target size in megabytes
            content_type: Type of content ("lorem", "code", "structured", "mixed")
            
        Returns:
            Generated content string
        """
        if size_mb:
            target_size = size_mb * 1024 * 1024
        elif size_kb:
            target_size = size_kb * 1024
        else:
            target_size = 1024  # Default 1KB
        
        content_parts = []
        current_size = 0
        
        while current_size < target_size:
            if content_type == "lorem":
                chunk = self._generate_lorem_chunk()
            elif content_type == "code":
                chunk = self._generate_code_chunk()
            elif content_type == "structured":
                chunk = self._generate_structured_chunk()
            else:  # mixed
                chunk = self._generate_mixed_chunk()
            
            content_parts.append(chunk)
            current_size += len(chunk.encode('utf-8'))
            
            # Add some spacing between chunks
            if current_size < target_size:
                spacing = "\n\n" + "=" * 50 + "\n\n"
                content_parts.append(spacing)
                current_size += len(spacing.encode('utf-8'))
        
        content = "".join(content_parts)
        
        # Trim to exact size if needed
        if len(content.encode('utf-8')) > target_size:
            # Binary search to find the right cut point
            content = self._trim_to_size(content, target_size)
        
        return content
    
    def _generate_lorem_chunk(self) -> str:
        """Generate a chunk of Lorem Ipsum text."""
        sentences = []
        words = self.LOREM_IPSUM.replace('\n', ' ').split()
        
        for _ in range(self.random.randint(5, 20)):  # 5-20 sentences per chunk
            sentence_length = self.random.randint(8, 25)  # 8-25 words per sentence
            sentence_words = self.random.choices(words, k=sentence_length)
            sentence = " ".join(sentence_words).capitalize() + "."
            sentences.append(sentence)
        
        return " ".join(sentences)
    
    def _generate_code_chunk(self) -> str:
        """Generate a chunk of code content."""
        base_code = self.random.choice(self.CODE_SAMPLES)
        
        # Add some random variations
        lines = base_code.strip().split('\n')
        
        # Add random comments
        for i in range(len(lines)):
            if self.random.random() < 0.2:  # 20% chance to add comment
                if lines[i].strip().startswith('def ') or lines[i].strip().startswith('class '):
                    lines[i] += f"  # Generated function {uuid.uuid4().hex[:8]}"
        
        # Add random variable names
        for i in range(3):
            var_name = f"temp_var_{uuid.uuid4().hex[:6]}"
            value = self.random.randint(1, 1000)
            lines.append(f"{var_name} = {value}")
        
        return '\n'.join(lines)
    
    def _generate_structured_chunk(self) -> str:
        """Generate structured document content."""
        template = self.random.choice(self.STRUCTURED_CONTENT_TEMPLATES)
        
        # Add some random sections
        additional_sections = []
        for i in range(self.random.randint(1, 3)):
            section_id = uuid.uuid4().hex[:8]
            section = f"""
## Additional Section {i+1}

This section covers {section_id} functionality and related components.
The implementation includes various optimizations and best practices.

### Key Features
- Feature A: High performance processing
- Feature B: Scalable architecture  
- Feature C: Comprehensive monitoring

### Technical Details
The technical implementation follows industry standards and includes:
- Proper error handling and logging
- Input validation and sanitization
- Performance monitoring and metrics
- Comprehensive test coverage
"""
            additional_sections.append(section)
        
        return template + "\n".join(additional_sections)
    
    def _generate_mixed_chunk(self) -> str:
        """Generate mixed content combining different types."""
        chunk_type = self.random.choice(["lorem", "code", "structured"])
        
        if chunk_type == "lorem":
            return self._generate_lorem_chunk()
        elif chunk_type == "code":
            return self._generate_code_chunk()
        else:
            return self._generate_structured_chunk()
    
    def _trim_to_size(self, content: str, target_size: int) -> str:
        """Trim content to approximately target size in bytes."""
        content_bytes = content.encode('utf-8')
        
        if len(content_bytes) <= target_size:
            return content
        
        # Binary search for the right position
        left, right = 0, len(content)
        
        while left < right:
            mid = (left + right + 1) // 2
            if len(content[:mid].encode('utf-8')) <= target_size:
                left = mid
            else:
                right = mid - 1
        
        return content[:left]


class SearchQueryGenerator:
    """Generator for realistic search queries."""
    
    COMMON_WORDS = [
        "document", "file", "content", "text", "data", "information", "system",
        "process", "method", "function", "class", "variable", "parameter",
        "result", "value", "object", "array", "string", "number", "boolean",
        "user", "admin", "account", "profile", "settings", "configuration",
        "database", "table", "record", "field", "column", "index", "query",
        "search", "filter", "sort", "pagination", "validation", "authentication",
        "authorization", "security", "performance", "optimization", "cache"
    ]
    
    TECHNICAL_TERMS = [
        "API", "REST", "HTTP", "JSON", "XML", "SQL", "NoSQL", "Redis",
        "PostgreSQL", "MongoDB", "Elasticsearch", "Docker", "Kubernetes",
        "microservices", "architecture", "framework", "library", "algorithm",
        "data structure", "optimization", "scalability", "availability",
        "consistency", "durability", "transaction", "ACID", "CAP theorem"
    ]
    
    def __init__(self):
        """Initialize the search query generator."""
        self.random = random.Random()
    
    def generate_queries(self, count: int) -> List[str]:
        """
        Generate a list of realistic search queries.
        
        Args:
            count: Number of queries to generate
            
        Returns:
            List of search query strings
        """
        queries = []
        
        for _ in range(count):
            query_type = self.random.choice(["single_word", "phrase", "technical", "compound"])
            
            if query_type == "single_word":
                query = self.random.choice(self.COMMON_WORDS)
            elif query_type == "phrase":
                words = self.random.choices(self.COMMON_WORDS, k=self.random.randint(2, 4))
                query = " ".join(words)
            elif query_type == "technical":
                query = self.random.choice(self.TECHNICAL_TERMS)
            else:  # compound
                part1 = self.random.choice(self.COMMON_WORDS)
                part2 = self.random.choice(self.TECHNICAL_TERMS)
                query = f"{part1} {part2}"
            
            queries.append(query)
        
        return queries
    
    def generate_query_based_on_content(self, content: str) -> str:
        """
        Generate a search query based on document content.
        
        Args:
            content: Document content to extract query terms from
            
        Returns:
            Search query string
        """
        # Extract words from content
        words = content.lower().split()
        # Filter out short words and common words
        meaningful_words = [w for w in words if len(w) > 3 and w.isalpha()]
        
        if meaningful_words:
            # Choose 1-3 words randomly
            query_words = self.random.choices(
                meaningful_words, 
                k=min(self.random.randint(1, 3), len(meaningful_words))
            )
            return " ".join(query_words)
        else:
            # Fallback to random query
            return self.random.choice(self.COMMON_WORDS)


class DocumentCorpusGenerator:
    """Generator for large document corpora for testing."""
    
    def __init__(self):
        """Initialize the corpus generator."""
        self.content_generator = DocumentContentGenerator()
        self.query_generator = SearchQueryGenerator()
    
    def generate_corpus_metadata(self, document_count: int, 
                                avg_size_kb: int = 10) -> List[Dict[str, Any]]:
        """
        Generate metadata for a document corpus.
        
        Args:
            document_count: Number of documents to generate metadata for
            avg_size_kb: Average document size in KB
            
        Returns:
            List of document metadata dictionaries
        """
        corpus_metadata = []
        
        for i in range(document_count):
            # Vary document sizes around the average
            size_variation = random.uniform(0.5, 2.0)  # 50% to 200% of average
            doc_size_kb = max(1, int(avg_size_kb * size_variation))
            
            # Choose content type
            content_type = random.choices(
                ["mixed", "lorem", "code", "structured"],
                weights=[0.4, 0.3, 0.2, 0.1]  # Mixed content is most common
            )[0]
            
            metadata = {
                "title": f"Document {i+1:06d}",
                "size_kb": doc_size_kb,
                "content_type": content_type,
                "tags": self._generate_tags(),
                "category": self._generate_category()
            }
            
            corpus_metadata.append(metadata)
        
        return corpus_metadata
    
    def _generate_tags(self) -> List[str]:
        """Generate random tags for a document."""
        tag_pool = [
            "important", "draft", "review", "approved", "archived",
            "technical", "business", "legal", "marketing", "research",
            "python", "javascript", "java", "react", "django",
            "api", "database", "frontend", "backend", "devops"
        ]
        
        num_tags = random.randint(0, 5)
        return random.sample(tag_pool, num_tags)
    
    def _generate_category(self) -> str:
        """Generate a random category for a document."""
        categories = [
            "Documentation", "Code", "Requirements", "Design",
            "Testing", "Deployment", "Operations", "Legal",
            "Marketing", "Research", "Training", "Reference"
        ]
        
        return random.choice(categories)
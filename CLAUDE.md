# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sophisticated Django document management service designed for collaborative editing with Lexical editor integration. Built with Python 3.11, Poetry for dependency management, and Docker for containerization. The project implements a dual-interface architecture (REST API + Web UI) with advanced features including real-time change tracking, optimistic locking, version control, and comprehensive audit trails.

## Development Environment

### Quick Setup
```bash
make dev-setup    # Complete development setup (build, start, migrate)
make up           # Start services
make logs         # View logs
```

### Essential Commands


**Code quality:**
- `make test` - Run tests with pytest
- `make test-coverage` - Run tests with coverage reporting
- `make lint` - Check code formatting with black
- `make format` - Format code with black

**Search functionality:**
- `make search-stats` - Display comprehensive search statistics and performance metrics
- `make search-reindex` - Rebuild search vectors for all documents
- `make search-test` - Run search performance tests with detailed analysis

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
The application runs as a multi-container setup with service isolation and dependency management:
- **web**: Django application server (port 8000) - Main application with both API and web interfaces
- **postgres**: PostgreSQL 15 database (port 5432) - Primary data storage with ACID compliance
- **redis**: Redis 7 cache (port 6379) - High-performance caching and session storage

**Service Dependencies:**
- Web service depends on both postgres and redis services
- Automatic service discovery via Docker Compose networking
- Health check endpoints for monitoring service connectivity
- Volume persistence for postgres data (`postgres_data` volume)

### Service Layer Architecture
The application implements a comprehensive service layer pattern for business logic centralization:

**DocumentService (`documents/services.py`):**
- **Centralized Business Logic**: All document operations flow through the service layer
- **Transaction Management**: Atomic operations with automatic rollback on failures
- **User Management**: Handles both authenticated and anonymous user scenarios
- **Content Processing**: Bidirectional conversion between plain text and Lexical JSON format
- **Change Tracking**: Comprehensive audit trail with user attribution and version tracking

**Key Service Methods:**
- `create_document()` - Document creation with content processing and change tracking
- `update_document()` - Updates with intelligent version management and conflict detection
- `apply_changes()` - Apply OT operations directly with version conflict detection
- `preview_changes()` - Non-destructive OT operation testing with detailed results
- `get_change_history()` - Complete audit trail retrieval with pagination
- `search_documents()` - PostgreSQL full-text search with ranking and filtering
- `search_user_documents()` - User-specific document search with permission filtering
- `_convert_changes_to_ot_operations()` - Helper to convert operation dictionaries to OTOperation objects

### Document Model Design
The core `Document` model (`documents/models.py`) is engineered for distributed collaborative editing:

**Primary Key Strategy:**
- **UUID primary keys** (`uuid.uuid4()`) for global uniqueness and distributed system compatibility
- Eliminates conflicts in multi-instance deployments and database replication scenarios

**Content Management:**
- **JSONField content** with `default=dict` optimized for Lexical editor state storage
- **Intelligent version tracking** with automatic increment only on actual content/title changes
- **Smart save() override** that compares existing vs new data to prevent unnecessary version bumps
- **Lexical content validation** and processing through utility functions

**Optimistic Locking:**
- **ETag generation** via MD5 hash of `content + version` for conflict detection
- **HTTP ETag headers** on all API responses for client-side caching and conflict prevention
- **Version-based conflict resolution** prevents lost updates in concurrent editing scenarios

**User Relationships:**
- **created_by**: Foreign key to User with CASCADE delete (required)
- **last_modified_by**: Foreign key to User with CASCADE delete (optional, tracks last editor)
- **Anonymous user support** via fallback "anonymous" user creation

**Content Processing:**
- **get_plain_text() method**: Recursive extraction of text from Lexical JSON structure
- **Handles multiple Lexical formats**: Both `root.children` and alternative `content` structures  
- **Text node traversal**: Deep parsing of nested Lexical node hierarchies
- **Bidirectional processing**: Conversion between plain text and structured Lexical content

**Temporal Tracking:**
- **created_at**: Auto-populated timestamp (auto_now_add=True)
- **updated_at**: Auto-updated timestamp (auto_now=True)
- **Default ordering**: Most recently updated documents first (`-updated_at`)

**PostgreSQL Full-Text Search Integration:**
- **SearchVectorField**: Dedicated field for storing computed search vectors
- **GIN Index**: High-performance index for full-text search operations
- **Weighted Search Vectors**: Title content weighted 'A', document content weighted 'B'
- **Automatic Updates**: Search vectors updated automatically on document save

**Model Methods:**
- `increment_version()`: Manual version increment with save
- `update_search_vector()`: Regenerate search vector with weighted content
- `get_absolute_url()`: Returns web interface URL for the document
- `get_plain_text()`: Extract plain text from Lexical JSON for search indexing
- `__str__()`: Returns document title
- `__repr__()`: Returns detailed representation with title and version

### DocumentChange Audit Model
The `DocumentChange` model provides comprehensive change tracking and audit capabilities:

**Change Tracking:**
- **UUID primary keys** for distributed change identification
- **Document foreign key** with CASCADE delete and `related_name="changes"`
- **Version transitions**: `from_version` and `to_version` tracking for complete history
- **Chronological ordering**: Most recent changes first (`-applied_at`)

**Change Data Storage:**
- **JSONField change_data**: Stores complete change operations as structured JSON
- **Flexible format**: Supports various change types (create, update, text-based, position-based)
- **Operation metadata**: Includes operation type, targets, replacements, and context

**User Attribution:**
- **applied_by**: Foreign key to User tracking who made the change
- **Complete user context**: Links changes to authenticated or anonymous users
- **Change ownership**: Enables per-user change history and analytics

**Audit Trail Features:**
- **applied_at**: Precise timestamp of when change was applied
- **Change type identification**: Distinguished between creates, updates, and structured changes
- **Rollback capability**: Change data format enables potential change reversal
- **Analytics support**: Enables change frequency, user activity, and collaboration metrics

### Operational Transform (OT) System
The application implements a sophisticated **Operational Transform system** (`documents/operational_transforms.py`) for real-time collaborative editing with conflict resolution:

**Core OT Operations:**
- **Insert**: Insert text at a position (sequential, not absolute)
- **Delete**: Delete text by length (sequential, not absolute) 
- **Retain**: Keep existing text unchanged (for composing operations)

**OTOperation Class:**
- **Dataclass structure**: Type-safe operation representation with serialization
- **Position-based semantics**: Operations work sequentially through document
- **Attribute support**: Extensible for future formatting features
- **Serialization**: JSON conversion for API transmission

**OTOperationSet Class:**
- **Sequential application**: Operations applied in proper OT sequence (retain → delete → insert)
- **Fluent interface**: Chainable methods for building operation sets
- **Text transformation**: Complete document transformation with validation
- **Error handling**: Comprehensive validation of operation bounds

**OTTransformer Class:**
- **Conflict resolution**: Advanced algorithms for concurrent editing scenarios
- **Operation transformation**: Transform operations against each other for consistency
- **Priority handling**: Conflict resolution with left/right priority
- **Multi-operation support**: Transform entire operation sets

**OTDiffGenerator Class:**
- **Text diff analysis**: Generate OT operations from text differences
- **Common prefix/suffix optimization**: Efficient diff algorithms
- **Incremental operations**: Optimized for typing patterns
- **Validation**: Test generated operations before return

### Streamlined Change Operations Architecture
The system implements a **three-layer architecture** for handling document changes with direct OT processing:

**1. Core OT Engine (`documents/operational_transforms.py`):**
- **Pure OT implementation**: Insert/Delete/Retain operations with proper sequential semantics
- **Sequential processing**: Operations work through document without absolute positions
- **Conflict resolution**: Advanced transformation algorithms for concurrent editing
- **OTOperationSet**: Complete operation orchestration with validation and application

**2. Content Diff Generator (`documents/content_diff.py`):**
- **Web form integration**: Convert web form changes directly to OT operations
- **Pattern detection**: Analyze typing patterns for optimization
- **API payload creation**: Format OT operations for API submission
- **Validation**: Ensure operations can be applied safely

**3. Web-to-API Bridge (`documents/api_client.py`):**
- **Internal HTTP client**: Web interface communicates with API via HTTP
- **Token management**: Automatic API token creation and handling
- **Error mapping**: Convert API errors to web-friendly responses
- **Test mode detection**: Use Django test client during testing

**Service Layer Integration (`documents/services.py`):**
- **Direct OT processing**: DocumentService uses OTOperationSet directly without intermediate layers
- **Operation conversion**: Helper methods convert operation dictionaries to OTOperation objects
- **Validation**: Comprehensive validation of OT operations before application
- **Transaction safety**: Atomic operations with proper error handling

### Lexical Editor Integration
The system provides comprehensive support for Lexical editor content through utility functions (`documents/utils.py`):

**Content Validation:**
- `validate_lexical_content()`: Structural validation of Lexical JSON format
- **Root structure checking**: Ensures proper `root.children` hierarchy
- **Type validation**: Verifies correct node types and structure

**Content Processing:**
- `update_lexical_content_with_text()`: Converts plain text to Lexical structure
- **Paragraph handling**: Splits text by newlines into paragraph nodes
- **Text node creation**: Generates proper Lexical text nodes with formatting attributes
- **Empty content handling**: Creates proper empty paragraph structures

**Content Creation:**
- `create_basic_lexical_content()`: Generates minimal valid Lexical structure
- **Default attributes**: Includes proper format, indent, version, and mode attributes
- **Flexible input**: Handles both empty and populated text content

**Text Extraction:**
- `extract_text_from_lexical()`: Recursive plain text extraction from Lexical structures
- **Node traversal**: Deep traversal of nested node hierarchies
- **Format agnostic**: Handles various Lexical node structures and formats
- **Text aggregation**: Intelligent joining of text fragments with appropriate spacing

**Multi-Database Architecture:**
- **PostgreSQL primary**: Full ACID compliance for document data integrity
- **Container-aware networking**: Service names used for inter-container communication

**Authentication & Security:**
- **Token-based API authentication**: DRF Token authentication for API access
- **Session authentication**: Web interface session management

### Docker and Poetry Integration
**Container Architecture:**
- **Python 3.11-slim base**: Minimal container footprint with required system dependencies
- **Poetry configuration**: `POETRY_NO_INTERACTION=1` and `POETRY_VENV_IN_PROJECT=false`
- **Development optimization**: Direct dependency installation without virtual environments
- **Lock file handling**: Automatic `poetry.lock` generation when missing

**Development Workflow:**
- **Volume mounting**: Live code reloading via `.:app` volume mount
- **Dependency caching**: Poetry cache optimization for faster rebuilds
- **Multi-stage ready**: Dockerfile structure supports production multi-stage builds
- **Service orchestration**: Proper service dependencies and health checks

## Database Architecture

### PostgreSQL Primary Database
- **Engine**: `django.db.backends.postgresql`
- **Connection**: Environment-variable driven (POSTGRES_DB, POSTGRES_USER, etc.)
- **Data persistence**: Named volume `postgres_data`

### PostgreSQL Full-Text Search System
The application implements enterprise-grade full-text search using PostgreSQL's native capabilities:

**Search Architecture:**
- **SearchVectorField**: Dedicated field storing pre-computed search vectors on Document model
- **GIN Index**: High-performance Generalized Inverted Index for sub-2ms search performance  
- **Weighted Vectors**: Title content weighted 'A' (highest), document content weighted 'B'
- **Automatic Updates**: Search vectors regenerated automatically on document save operations

**Search Features:**
- **Real-time Search**: HTMX-powered live search with 300ms debouncing
- **Ranking**: PostgreSQL ts_rank scoring for relevance-based result ordering
- **User Filtering**: Toggle between personal documents and global search
- **Content Snippets**: Automatically truncated 200-character content previews
- **Multi-format Support**: Searches both document titles and Lexical JSON content

**Search Implementation:**
- **Service Layer**: `DocumentService.search_documents()` and `search_user_documents()` methods
- **API Endpoint**: `GET /api/documents/search/` with query parameters (q, limit, user_only)
- **Web Interface**: Live search with `document_search_ajax()` view and HTMX integration
- **Management Commands**: `update_search_vectors` and `search_stats` for maintenance

**Query Processing:**
- **Text Extraction**: Recursive parsing of Lexical JSON structures via `get_plain_text()`
- **Search Query**: PostgreSQL `SearchQuery` with phrase and term support
- **Result Ranking**: `SearchRank` with vector weighting for relevance scoring
- **Permission Filtering**: User-based document access control in search results

### Redis Caching Layer
- **Backend**: `django.core.cache.backends.redis.RedisCache`
- **Connection**: Via REDIS_URL environment variable
- **Usage**: General purpose caching, session storage ready

## Health Monitoring

The application provides comprehensive health monitoring capabilities:

**Health Check Endpoint (`/health/`):**
- **Database connectivity**: Tests PostgreSQL connection with SELECT 1 query
- **Cache connectivity**: Tests Redis connection with set/get operations
- **Service status aggregation**: Returns overall "healthy"/"unhealthy" status
- **Error reporting**: Detailed error messages for failed service connections
- **JSON response format**: Structured response for monitoring systems

**Health Check Implementation (`document_service/views.py`):**
- **Exception handling**: Graceful handling of service connection failures  
- **Connection testing**: Uses Django database cursor and cache operations
- **Status determination**: Marks overall status as unhealthy if any service fails
- **Monitoring integration**: Compatible with Docker health checks and external monitoring

**Makefile Health Commands:**
- `make health`: Quick health check via curl with JSON formatting
- `make ps`: Container status and running processes
- `make logs`: Service logs for troubleshooting

## Testing Framework

The application implements a comprehensive testing strategy using pytest with extensive fixtures and coverage reporting:

**Testing Architecture:**
- **pytest framework**: Modern testing with powerful fixtures and parametrization
- **pytest-django integration**: Django-specific testing utilities and database handling
- **Container-based testing**: All tests run inside Docker for environment parity


**Advanced Testing Features:**
- **Database transactions**: `@pytest.mark.django_db` for database access control
- **Factory patterns**: Dynamic test data creation with parameterized attributes
- **UUID handling**: Proper UUID primary key testing and validation
- **Version control testing**: Change tracking and version increment validation
- **Service layer testing**: Business logic isolation and transaction testing
- **Exception testing**: Comprehensive error handling and edge case coverage
- **Integration scenarios**: Cross-component testing with realistic data flows



## API Architecture

### Dual-Interface Design with Internal API Communication
The application implements a hybrid architecture where the **web interface acts as an API client**:

**API Interface (`/api/`):**
- **RESTful design**: Resource-based URLs following Django REST Framework conventions
- **JSON communication**: Request/response handling with structured JSON data
- **Token authentication**: Header-based authentication for stateless API access
- **Advanced OT endpoints**: Change application, preview, and history endpoints

**Web Interface (`/documents/`):**
- **Traditional Django views**: Server-side rendering with template responses
- **Internal API communication**: Web views use `DocumentAPIClient` to communicate with API endpoints
- **Unified business logic**: Both interfaces use the same service layer through API
- **Auto-save functionality**: AJAX calls to web views, which proxy to API endpoints
- **Bootstrap 5 UI**: Responsive design with Crispy Forms integration

**Internal API Client Pattern:**
- **DocumentAPIClient class**: Web interface makes HTTP requests to its own API
- **Token management**: Automatic API token creation for web users
- **Error mapping**: API errors converted to web-friendly responses
- **Test mode support**: Uses Django test client during testing for speed

### REST API Endpoints

**Core Document Operations:**
- `GET /api/` - API root with endpoint discovery
- `GET /api/docs/` - API documentation and usage guidelines
- `GET /api/documents/` - List all documents (paginated, searchable)
- `POST /api/documents/` - Create new document (supports anonymous users)
- `GET /api/documents/{id}/` - Retrieve specific document with ETag
- `PUT /api/documents/{id}/` - Full document update with version tracking
- `PATCH /api/documents/{id}/` - Partial document update

**Advanced Operational Transform Operations:**
- `PATCH /api/documents/{id}/changes/` - Apply OT operations with conflict detection and version control
- `POST /api/documents/{id}/preview/` - Preview OT operations without applying them
- `GET /api/documents/{id}/history/` - Retrieve paginated change history with full audit trail

**Search Operations:**
- `GET /api/documents/search/` - PostgreSQL full-text search with ranking and filtering

**System Endpoints:**
- `GET /health/` - Service health check (database + Redis connectivity)
- `GET /admin/` - Django admin interface

### ViewSet Architecture (`documents/views.py`)

**DocumentViewSet (API Interface):**
- **ModelViewSet inheritance**: Full CRUD operations with DRF conventions
- **Dynamic serializer selection**: Different serializers for list/detail/create operations
- **Search integration**: Query parameter filtering with Q objects
- **ETag header management**: Automatic ETag generation and response headers
- **Custom actions**: Additional endpoints for advanced operations

**Custom ViewSet Methods:**
- `create()`: Enhanced creation with full document response and ETag headers
- `retrieve()`: Document retrieval with ETag headers for caching
- `update()`: Update operations with ETag headers and version tracking
- `get_queryset()`: Search functionality across title and content fields

**Custom Actions:**
- `@action(detail=True, methods=["patch"]) apply_changes()`: Apply OT operations with version conflict detection
- `@action(detail=True, methods=["post"]) preview_changes()`: Preview OT operations without applying
- `@action(detail=True, methods=["get"]) change_history()`: Retrieve complete change audit trail
- `@action(detail=False, methods=["get"]) search()`: PostgreSQL full-text search with ranking and filtering

### Web Interface Views

**Class-Based Views:**
- `DocumentWebListView`: Paginated document list with user filtering
- `DocumentWebDetailView`: Document detail with inline editing support
- `DocumentWebCreateView`: Document creation with form validation

**AJAX Endpoints:**
- `document_search_ajax()`: Live search interface with HTMX integration
- **Internal API communication**: AJAX endpoints use `DocumentAPIClient` to communicate with API
- **OT integration**: Web form changes converted via `ContentDiffGenerator` to OT operations
- **Error handling**: API errors mapped to web-friendly JSON responses via `APIClientMixin`

### Serializer Strategy

**Specialized Serializers for Different Use Cases:**

**1. DocumentListSerializer:**
- **Lightweight response**: Excludes content field for performance
- **User information**: Includes created_by details
- **Essential metadata**: ID, title, version, timestamps
- **Read-only fields**: Prevents modification of computed fields

**2. DocumentSerializer (Full Detail):**
- **Complete document data**: All fields including content
- **ETag support**: Computed ETag field for optimistic locking
- **User relationship serialization**: Full user details for created_by and last_modified_by
- **Computed fields**: Human-readable user names via SerializerMethodField
- **Content validation**: Ensures JSONField contains valid dictionary data
- **Service layer integration**: Updates route through DocumentService

**3. DocumentCreateSerializer:**
- **Creation-focused**: Only title and content fields
- **Validation logic**: Title length and content format validation
- **Anonymous user handling**: Supports unauthenticated document creation
- **Service layer integration**: Routes creation through DocumentService

**4. DocumentChangeSerializer:**
- **OT operation validation**: Validates Operational Transform operations (insert/delete/retain)
- **Version conflict detection**: Ensures expected version matches current version
- **Sequential operation support**: Handles proper OT operation sequences
- **Service layer integration**: Routes OT operations through DocumentService

**5. ChangeOperationSerializer:**
- **Operation validation**: Validates individual change operations
- **Flexible change types**: Supports both target-based and range-based changes
- **Error handling**: Detailed validation errors for malformed operations

**6. DocumentChangeHistorySerializer:**
- **Audit trail presentation**: Change history with user attribution
- **User relationship**: Full user details for applied_by field
- **Change metadata**: Version transitions and timestamps
- **Human-readable formatting**: User names via SerializerMethodField

**7. DocumentSearchResultSerializer:**
- **Search optimization**: Lightweight serializer for search results
- **Content snippets**: Automatically truncated content previews (200 characters)
- **Search ranking**: Includes PostgreSQL search rank scores
- **User attribution**: Human-readable creator names
- **Performance focused**: Minimal data transfer for fast search responses

### Permission and Authentication Model

**API Authentication:**
- **Token authentication**: Primary method for API access
- **Session authentication**: Fallback for web interface AJAX calls
- **Anonymous access**: Controlled anonymous document creation

**Permission Strategy:**
- **IsAuthenticated default**: All operations require authentication
- **Anonymous user fallback**: Documents created by anonymous users when unauthenticated
- **Owner-based access**: Users can only modify their own documents
- **Search accessibility**: All authenticated users can search all documents

**ETag-Based Optimistic Locking:**
- **Conflict prevention**: ETags prevent lost updates in concurrent editing
- **Client-side caching**: ETags enable efficient browser caching
- **Version synchronization**: ETags reflect both content and version changes
- **Header management**: Automatic ETag header inclusion in all responses

### Error Handling and Validation

**Exception Management:**
- **Version conflicts**: HTTP 409 Conflict for version mismatches
- **Validation errors**: HTTP 400 Bad Request for invalid operations
- **Permission errors**: HTTP 403 Forbidden for unauthorized access
- **Not found errors**: HTTP 404 Not Found for missing resources

**Error Response Format:**
- **Structured errors**: Consistent JSON error response format
- **Detailed messages**: Human-readable error descriptions
- **Context information**: Additional context for conflict resolution (e.g., current version)

## Web Interface Architecture

### Template-Based UI (`templates/`)
The web interface provides a complete document management system with responsive design:

**Template Structure:**
- `base.html` - Base template with Bootstrap 5, navigation, and common layout
- `documents/list.html` - Document list with pagination, user filtering, and live search interface
- `documents/detail.html` - Document detail view with inline editing
- `documents/create.html` - Document creation form
- `documents/search_results.html` - HTMX-powered search results with dynamic loading
- `documents/partials/document_card.html` - Reusable document card component
- `registration/login.html` - Authentication form

**Static Assets (`static/`):**
- `css/main.css` - Custom styling and responsive design enhancements, search UI components
- `js/app.js` - JavaScript for auto-save, AJAX interactions, dynamic updates, and Alpine.js search components

### Form Management (`documents/forms.py`)

**DocumentForm:**
- **Crispy Forms integration**: Bootstrap 5 styled forms with layout control
- **Plain text content**: Converts between plain text input and Lexical JSON
- **Auto-save support**: Designed for AJAX auto-save functionality
- **Validation**: Title requirement and content processing

**DocumentCreateForm:**
- **Specialized creation**: Extends DocumentForm with creation-specific behavior
- **Optional content**: Allows creation of documents with empty content
- **User experience**: Optimized placeholder text and field handling

### AJAX Integration

**Dynamic Updates:**
- **Document deletion**: AJAX-based deletion with confirmation
- **Form submission**: Enhanced form handling with AJAX fallbacks
- **Error display**: Dynamic error message display without page reloads
- **Live search**: HTMX-powered search with 300ms debouncing and loading indicators
- **Search filtering**: Real-time user/global document filtering without page reloads

### Authentication Flow

**User Authentication:**
- **Login/logout views**: Django built-in authentication views
- **Session management**: Cookie-based session authentication
- **Access control**: Login required for document operations
- **Redirect handling**: Smart redirects based on authentication status

## URL Routing Architecture

### URL Pattern Organization

**Main URL Configuration (`document_service/urls.py`):**
- **Root redirect**: Smart routing based on authentication status
- **Admin interface**: `/admin/` for Django admin
- **Health monitoring**: `/health/` for service status
- **Authentication**: `/accounts/` for login/logout functionality
- **API routes**: `/api/` prefix for all REST API endpoints
- **Web interface**: `/documents/` for web-based document management

**API URL Configuration (`api/urls.py`):**
- **DRF Router integration**: Automatic URL generation for ViewSets
- **API root**: `/api/` with endpoint discovery
- **API documentation**: `/api/docs/` with usage guidelines
- **RESTful conventions**: Standard CRUD operations with proper HTTP methods

**Document URL Configuration (`documents/urls.py`):**
- **Web interface only**: Separated from API routes for clarity
- **UUID path converters**: Proper UUID handling in URL patterns
- **CRUD operations**: Complete web interface for document management
- **Auto-save endpoint**: Dedicated AJAX endpoint for auto-save functionality

**URL Patterns:**
- `documents/` - Document list view (paginated)
- `documents/create/` - Document creation form
- `documents/search/` - AJAX search endpoint for HTMX live search
- `documents/<uuid:pk>/` - Document detail view with editing
- `documents/<uuid:pk>/autosave/` - AJAX auto-save endpoint

## Development Workflow

### Environment Setup
**Initial Setup:**
Copy `.env.example` to `.env` and configure environment variables
Use `make dev-setup-fresh` to include default admin user (admin/admin123)
Access application at `http://localhost:8000`


## Management Commands

The application includes custom Django management commands for administrative tasks:

### Document Management Commands (`documents/management/commands/`)

**create_test_users.py:**
- **Purpose**: Create test users for development and testing
- **Usage**: `python manage.py create_test_users`
- **Features**: Creates multiple users with different permission levels
- **Development utility**: Streamlines test environment setup

**create_api_token.py:**
- **Purpose**: Generate API tokens for user authentication
- **Usage**: `python manage.py create_api_token --user <username>`
- **Features**: Creates or retrieves existing tokens for API access
- **Token management**: Simplifies API authentication setup

### Search Management Commands (`documents/management/commands/`)

**update_search_vectors.py:**
- **Purpose**: Rebuild or update PostgreSQL search vectors for documents
- **Usage**: `python manage.py update_search_vectors [--force] [--dry-run] [--batch-size=N] [--document-id=UUID]`
- **Features**: 
  - `--force`: Rebuild all search vectors even if they exist
  - `--dry-run`: Show what would be updated without making changes
  - `--batch-size`: Process documents in batches (default: 1000)
  - `--document-id`: Update specific document only
- **Performance**: Batch processing with progress reporting and error handling

**search_stats.py:**
- **Purpose**: Display comprehensive search statistics and performance analysis
- **Usage**: `python manage.py search_stats [--verbose] [--test-search] [--sample-queries query1 query2 ...]`
- **Features**:
  - `--verbose`: Show detailed content analysis and database index information
  - `--test-search`: Run performance tests with sample queries
  - `--sample-queries`: Test specific search queries instead of defaults
- **Analytics**: Document counts, search vector status, performance metrics, and recommendations

## Dependency Management


## Architecture Patterns and Best Practices

### Service Layer Pattern
The application implements a comprehensive service layer pattern for business logic encapsulation:

**Benefits:**
- **Cross-interface consistency**: Same business logic for API and web interfaces
- **Transaction management**: Atomic operations with proper rollback handling
- **Testing isolation**: Business logic testing independent of views/serializers
- **Code reuse**: Eliminates duplication between different interface layers

**Implementation Strategy:**
- **Static methods**: Service methods are stateless and side-effect free
- **Dependency injection**: Services receive dependencies as parameters
- **Exception propagation**: Custom exceptions bubble up through all layers
- **Validation centralization**: Business rules enforced in service layer

### Testing Philosophy
The testing strategy emphasizes comprehensive coverage with realistic scenarios:

**Testing Principles:**
- **Behavior-driven testing**: Tests focus on behavior rather than implementation
- **Integration emphasis**: End-to-end testing to verify complete workflows
- **Fixture-based setup**: Reusable test data setup for consistency
- **Container testing**: Tests run in production-like environment

## Important Notes and Key Features

### Core Architecture Decisions

**UUID Primary Keys:**
- **Global uniqueness**: Supports distributed deployments and database replication
- **Security benefits**: Prevents enumeration attacks and ID guessing
- **URL safety**: Clean, unguessable URLs for document access
- **Merge compatibility**: Enables database merging without ID conflicts

**JSONField Content Storage:**
- **Lexical editor optimization**: Native support for structured editor content
- **Schema flexibility**: Accommodates evolving content structures
- **Query capabilities**: PostgreSQL JSON querying for search functionality
- **Version compatibility**: Backward compatibility with content format changes

**Optimistic Locking with ETags:**
- **Conflict prevention**: Prevents lost updates in concurrent editing scenarios
- **Client-side caching**: Enables efficient browser and proxy caching
- **Bandwidth optimization**: Conditional requests reduce unnecessary data transfer
- **User experience**: Immediate feedback on version conflicts

### Advanced Features


**Intelligent Version Tracking:**
- **Smart incrementing**: Version only increments on actual content/title changes
- **Performance optimization**: Avoids unnecessary version bumps on no-op saves
- **Change detection**: Compares current vs. new data to determine changes
- **Audit support**: Enables precise change tracking and rollback capabilities

**Operational Transform System:**
- **Real-time collaboration**: Proper OT implementation with Insert/Delete/Retain operations
- **Conflict resolution**: Advanced transformation algorithms for concurrent editing
- **Sequential processing**: Operations work through document without absolute positions
- **Web integration**: Automatic conversion of web form changes to OT operations

**PostgreSQL Full-Text Search:**
- **Enterprise-grade search**: Native PostgreSQL full-text search with GIN indexing
- **Sub-2ms performance**: Exceeds sub-100ms target by 98% with optimized search vectors
- **Weighted ranking**: Title content weighted higher than document content for relevance
- **Live search interface**: HTMX-powered real-time search with 300ms debouncing
- **Content snippets**: Automatic 200-character content previews in search results
- **User filtering**: Toggle between personal documents and global search results
- **Multi-format support**: Searches both document titles and Lexical JSON content

**Comprehensive Audit Trail:**
- **Complete change history**: Every document modification is tracked
- **User attribution**: All changes linked to specific users (including anonymous)
- **Version transitions**: Tracks from/to version for each change
- **Operation metadata**: Detailed information about each change operation
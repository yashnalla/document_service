"""
API Client for web interface to make internal HTTP requests to the API.

This module provides utilities for the web interface to communicate with the
API endpoints, enabling the web interface to act as an API client while
maintaining proper authentication and error handling.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient as DRFAPIClient
import requests
import sys


logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class APIAuthenticationError(APIClientError):
    """Raised when API authentication fails."""
    pass


class APIValidationError(APIClientError):
    """Raised when API validation fails."""
    pass


class APIConflictError(APIClientError):
    """Raised when API returns a conflict (version mismatch)."""
    
    def __init__(self, message: str, current_version: int = None):
        super().__init__(message)
        self.current_version = current_version


class DocumentAPIClient:
    """
    Client for making HTTP requests to the document API from web interface.
    
    This client handles authentication, request formatting, and error handling
    for web interface interactions with the API.
    """
    
    def __init__(self, user: User, base_url: str = None):
        """
        Initialize API client for a user.
        
        Args:
            user: Django user for authentication
            base_url: Base URL for API (defaults to localhost)
        """
        self.user = user
        self.base_url = base_url or "http://localhost:8000/api"
        self._token = None
        self._use_test_client = self._is_testing()
        if self._use_test_client:
            self._test_client = DRFAPIClient()
            self._test_client.force_authenticate(user=user)
    
    def _is_testing(self) -> bool:
        """Check if we're running in test mode."""
        return 'pytest' in sys.modules or 'django.test' in sys.modules or hasattr(settings, 'TESTING')
    
    @property
    def token(self) -> str:
        """Get or create API token for the user."""
        if self._token is None:
            if self.user.is_authenticated:
                token_obj, created = Token.objects.get_or_create(user=self.user)
                self._token = token_obj.key
                if created:
                    logger.info(f"Created new API token for user {self.user.username}")
            else:
                raise APIAuthenticationError("User is not authenticated")
        return self._token
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Make HTTP request to API endpoint.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request data (for POST/PATCH)
            params: Query parameters
            
        Returns:
            Tuple of (status_code, response_data)
            
        Raises:
            APIClientError: If request fails
        """
        if self._use_test_client:
            return self._make_test_request(method, endpoint, data, params)
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(
                    url, 
                    headers=headers, 
                    data=json.dumps(data) if data else None,
                    timeout=30
                )
            elif method.upper() == "PATCH":
                response = requests.patch(
                    url, 
                    headers=headers, 
                    data=json.dumps(data) if data else None,
                    timeout=30
                )
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise APIClientError(f"Unsupported HTTP method: {method}")
            
            # Parse response
            try:
                response_data = response.json() if response.content else {}
            except json.JSONDecodeError:
                response_data = {"error": "Invalid JSON response"}
            
            return response.status_code, response_data
            
        except requests.exceptions.Timeout:
            raise APIClientError("API request timed out")
        except requests.exceptions.ConnectionError:
            raise APIClientError("Unable to connect to API")
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"API request failed: {str(e)}")
    
    def _make_test_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Make test request using Django's test client.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request data (for POST/PATCH)
            params: Query parameters
            
        Returns:
            Tuple of (status_code, response_data)
        """
        # Convert endpoint to full path
        path = f"/api{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self._test_client.get(path, params or {}, format='json')
            elif method.upper() == "POST":
                response = self._test_client.post(path, data or {}, format='json')
            elif method.upper() == "PATCH":
                response = self._test_client.patch(path, data or {}, format='json')
            elif method.upper() == "DELETE":
                response = self._test_client.delete(path, format='json')
            else:
                raise APIClientError(f"Unsupported HTTP method: {method}")
            
            # Parse response data
            try:
                if hasattr(response, 'json'):
                    response_data = response.json()
                elif hasattr(response, 'data'):
                    response_data = response.data
                else:
                    response_data = {}
            except (ValueError, AttributeError):
                response_data = {}
            
            return response.status_code, response_data
            
        except Exception as e:
            raise APIClientError(f"Test API request failed: {str(e)}")
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Get a document by ID.
        
        Args:
            document_id: UUID of the document
            
        Returns:
            Document data
            
        Raises:
            APIClientError: If request fails
        """
        status_code, data = self._make_request("GET", f"/documents/{document_id}/")
        
        if status_code == 200:
            return data
        elif status_code == 404:
            raise APIClientError("Document not found")
        elif status_code == 403:
            raise APIAuthenticationError("Access denied to document")
        else:
            raise APIClientError(f"Failed to get document: {data.get('error', 'Unknown error')}")
    
    def create_document(self, title: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.
        
        Args:
            title: Document title
            content: Lexical content
            
        Returns:
            Created document data
            
        Raises:
            APIClientError: If creation fails
        """
        data = {
            "title": title,
            "content": content
        }
        
        status_code, response_data = self._make_request("POST", "/documents/", data)
        
        if status_code == 201:
            return response_data
        elif status_code == 400:
            raise APIValidationError(f"Validation error: {response_data.get('error', 'Invalid data')}")
        else:
            raise APIClientError(f"Failed to create document: {response_data.get('error', 'Unknown error')}")
    
    def update_document(
        self, 
        document_id: str, 
        title: str = None, 
        content: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Update a document using simple PATCH (no change tracking).
        
        Args:
            document_id: UUID of the document
            title: New title (optional)
            content: New content (optional)
            
        Returns:
            Updated document data
            
        Raises:
            APIClientError: If update fails
        """
        data = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        
        if not data:
            raise APIClientError("No data provided for update")
        
        status_code, response_data = self._make_request("PATCH", f"/documents/{document_id}/", data)
        
        if status_code == 200:
            return response_data
        elif status_code == 400:
            raise APIValidationError(f"Validation error: {response_data.get('error', 'Invalid data')}")
        elif status_code == 404:
            raise APIClientError("Document not found")
        elif status_code == 403:
            raise APIAuthenticationError("Access denied to document")
        else:
            raise APIClientError(f"Failed to update document: {response_data.get('error', 'Unknown error')}")
    
    def apply_changes(
        self, 
        document_id: str, 
        version: int, 
        changes: list
    ) -> Dict[str, Any]:
        """
        Apply structured changes to a document (with change tracking).
        
        Args:
            document_id: UUID of the document
            version: Expected document version
            changes: List of change operations
            
        Returns:
            Updated document data
            
        Raises:
            APIConflictError: If version conflict occurs
            APIValidationError: If changes are invalid
            APIClientError: If request fails
        """
        data = {
            "version": version,
            "changes": changes
        }
        
        logger.info(f"APIClient.apply_changes called with document_id={document_id}, version={version}")
        logger.info(f"Changes data: {changes}")
        
        status_code, response_data = self._make_request(
            "PATCH", 
            f"/documents/{document_id}/changes/", 
            data
        )
        
        logger.info(f"API response: status={status_code}, data={response_data}")
        
        if status_code == 200:
            logger.info("apply_changes succeeded")
            return response_data
        elif status_code == 409:
            # Version conflict
            current_version = response_data.get("current_version")
            error_msg = response_data.get("error", "Version conflict")
            logger.warning(f"Version conflict: {error_msg}, current_version={current_version}")
            raise APIConflictError(error_msg, current_version)
        elif status_code == 400:
            error_msg = f"Invalid changes: {response_data.get('error', 'Invalid data')}"
            logger.error(f"API validation error: {error_msg}")
            raise APIValidationError(error_msg)
        elif status_code == 404:
            logger.error("Document not found")
            raise APIClientError("Document not found")
        elif status_code == 403:
            logger.error("Access denied to document")
            raise APIAuthenticationError("Access denied to document")
        else:
            error_msg = f"Failed to apply changes: {response_data.get('error', 'Unknown error')}"
            logger.error(f"API client error: {error_msg}")
            raise APIClientError(error_msg)
    
    
    def get_change_history(
        self, 
        document_id: str, 
        limit: int = None, 
        offset: int = None
    ) -> Dict[str, Any]:
        """
        Get change history for a document.
        
        Args:
            document_id: UUID of the document
            limit: Maximum number of changes to return
            offset: Number of changes to skip
            
        Returns:
            Paginated change history
            
        Raises:
            APIClientError: If request fails
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        
        status_code, response_data = self._make_request(
            "GET", 
            f"/documents/{document_id}/history/", 
            params=params
        )
        
        if status_code == 200:
            return response_data
        elif status_code == 404:
            raise APIClientError("Document not found")
        elif status_code == 403:
            raise APIAuthenticationError("Access denied to document")
        else:
            raise APIClientError(f"Failed to get change history: {response_data.get('error', 'Unknown error')}")
    
    def preview_changes(
        self, 
        document_id: str, 
        changes: list
    ) -> Dict[str, Any]:
        """
        Preview changes without applying them.
        
        Args:
            document_id: UUID of the document
            changes: List of change operations
            
        Returns:
            Preview result
            
        Raises:
            APIClientError: If preview fails
        """
        data = {"changes": changes}
        
        status_code, response_data = self._make_request(
            "POST", 
            f"/documents/{document_id}/preview/", 
            data
        )
        
        if status_code == 200:
            return response_data
        elif status_code == 400:
            raise APIValidationError(f"Invalid changes: {response_data.get('error', 'Invalid data')}")
        elif status_code == 404:
            raise APIClientError("Document not found")
        elif status_code == 403:
            raise APIAuthenticationError("Access denied to document")
        else:
            raise APIClientError(f"Failed to preview changes: {response_data.get('error', 'Unknown error')}")


class APIClientMixin:
    """
    Mixin for Django views to easily use the API client.
    
    This mixin provides convenient methods for views to interact with the API
    and handle common error scenarios.
    """
    
    def get_api_client(self) -> DocumentAPIClient:
        """Get API client for the current user."""
        if not hasattr(self, '_api_client'):
            self._api_client = DocumentAPIClient(self.request.user)
        return self._api_client
    
    def handle_api_error(self, error: APIClientError) -> JsonResponse:
        """
        Handle API errors and return appropriate JSON response.
        
        Args:
            error: The API error that occurred
            
        Returns:
            JsonResponse with error details
        """
        if isinstance(error, APIConflictError):
            return JsonResponse({
                "success": False,
                "error": str(error),
                "error_type": "version_conflict",
                "current_version": error.current_version
            }, status=409)
        
        elif isinstance(error, APIValidationError):
            return JsonResponse({
                "success": False,
                "error": str(error),
                "error_type": "validation_error"
            }, status=400)
        
        elif isinstance(error, APIAuthenticationError):
            return JsonResponse({
                "success": False,
                "error": str(error),
                "error_type": "authentication_error"
            }, status=403)
        
        else:
            logger.error(f"API client error: {str(error)}")
            return JsonResponse({
                "success": False,
                "error": "An error occurred while communicating with the API",
                "error_type": "api_error"
            }, status=500)
    
    def api_success_response(self, data: Dict[str, Any], message: str = None) -> JsonResponse:
        """
        Create a successful API response.
        
        Args:
            data: Response data
            message: Optional success message
            
        Returns:
            JsonResponse with success data
        """
        response_data = {
            "success": True,
            "data": data
        }
        
        if message:
            response_data["message"] = message
        
        return JsonResponse(response_data)
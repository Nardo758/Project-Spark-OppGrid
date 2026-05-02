"""
Standard response schemas for all API endpoints
Ensures consistent response format across the entire API
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ErrorDetail(BaseModel):
    """Error details"""
    code: str = Field(..., description="Error code (e.g., VALIDATION_ERROR)")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[str]] = Field(default_factory=list, description="Additional error details")


class ResponseMeta(BaseModel):
    """Metadata included with all responses"""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp in ISO 8601")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID")


class PaginationMeta(ResponseMeta):
    """Pagination metadata for list responses"""
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Number of items skipped")
    total_count: int = Field(..., description="Total number of items")
    has_more: bool = Field(..., description="Whether there are more items")


class SuccessResponse(BaseModel):
    """Standard success response wrapper"""
    success: bool = Field(default=True, description="Success indicator")
    data: Any = Field(..., description="Response data")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "Example"},
                "meta": {
                    "timestamp": "2026-05-02T14:00:00Z",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }


class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper"""
    success: bool = Field(default=True, description="Success indicator")
    data: List[Any] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [{"id": 1}, {"id": 2}],
                "meta": {
                    "limit": 20,
                    "offset": 0,
                    "total_count": 1250,
                    "has_more": True,
                    "timestamp": "2026-05-02T14:00:00Z",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""
    success: bool = Field(default=False, description="Success indicator")
    error: ErrorDetail = Field(..., description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": ["Field 'email' is required"]
                }
            }
        }


def create_success_response(data: Any, meta: Optional[ResponseMeta] = None) -> Dict[str, Any]:
    """Create a standardized success response"""
    if meta is None:
        meta = ResponseMeta()
    
    return {
        "success": True,
        "data": data,
        "meta": meta.model_dump()
    }


def create_paginated_response(
    data: List[Any],
    total_count: int,
    limit: int = 20,
    offset: int = 0,
    meta: Optional[PaginationMeta] = None
) -> Dict[str, Any]:
    """Create a standardized paginated response"""
    if meta is None:
        meta = PaginationMeta(
            limit=limit,
            offset=offset,
            total_count=total_count,
            has_more=offset + limit < total_count
        )
    
    return {
        "success": True,
        "data": data,
        "meta": meta.model_dump()
    }


def create_error_response(
    code: str,
    message: str,
    details: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a standardized error response"""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or []
        }
    }

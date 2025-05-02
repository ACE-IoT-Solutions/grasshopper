"""Pydantic models for API"""

from typing import List, Optional

from pydantic import BaseModel, Field


class IPAddress(BaseModel):
    """IP Address with subnet mask model"""

    ip_address: str = Field(description="IP address with subnet mask")


class IPAddressList(BaseModel):
    """List of IP addresses with subnet mask included model"""

    ip_address_list: List[str]


class FileList(BaseModel):
    """List of files model"""

    file_list: List[str]


class CompareTTLFiles(BaseModel):
    """TTL Files to compare model"""

    ttl_1: str
    ttl_2: str


class MessageResponse(BaseModel):
    """Standard message response"""

    message: str


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str


class FileUploadResponse(BaseModel):
    """File upload response"""

    message: str
    file_path: str

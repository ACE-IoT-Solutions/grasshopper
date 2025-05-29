"""
Pydantic models for FastAPI request and response serialization.

This module defines the data models used for validating, serializing, and deserializing
data in the Grasshopper API. These models are used with FastAPI to:
- Validate request data
- Generate OpenAPI/Swagger documentation
- Serialize responses
- Provide type hints for request and response data
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class IPAddress(BaseModel):
    """
    Model for representing an IP address with optional subnet mask.

    This model is used for requests that require an IP address, particularly
    for BBMD and subnet configuration operations.
    """

    ip_address: str = Field(
        description="IP address with optional subnet mask (e.g., '192.168.1.1' or '192.168.1.0/24')"
    )


class IPAddressList(BaseModel):
    """
    Model for representing a list of IP addresses.

    This model is used for responses that return multiple IP addresses,
    such as listing configured BBMDs or subnets.
    """

    ip_address_list: List[str] = Field(
        description="List of IP addresses with optional subnet masks"
    )


class FileList(BaseModel):
    """
    Model for representing a list of files.

    This model is used for responses that return file listings,
    such as listing available TTL files or comparison results.
    """

    file_list: List[str] = Field(description="List of filenames")


class CompareTTLFiles(BaseModel):
    """
    Model for representing a pair of TTL files to compare.

    This model is used for requests to the TTL comparison endpoint,
    where two TTL files need to be specified for comparison.
    """

    ttl_1: str = Field(description="Filename of the first TTL file")
    ttl_2: str = Field(description="Filename of the second TTL file")


class MessageResponse(BaseModel):
    """
    Standard success response with a message.

    This model is used for API responses that return a success message,
    such as when a file is successfully deleted or an operation completes.
    """

    message: str = Field(
        description="Success message describing the result of the operation"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response with an error message.

    This model is used for API responses that return an error message,
    such as when a file is not found or an operation fails.
    """

    error: str = Field(description="Error message describing what went wrong")


class FileUploadResponse(BaseModel):
    """
    Response model for successful file uploads.

    This model is used for API responses after a file has been successfully
    uploaded, providing both a success message and the path where the file
    was saved.
    """

    message: str = Field(description="Success message confirming the file was uploaded")
    file_path: str = Field(description="Path where the uploaded file was saved")

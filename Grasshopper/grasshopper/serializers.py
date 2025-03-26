"""Serializers for API"""

from typing import List

from pydantic import BaseModel, Field


class IPAddress(BaseModel):
    """IP Address with subnet mask"""

    ip_address: str = Field(..., description="IP address with subnet mask")


class IPAddressList(BaseModel):
    """List of IP addresses with subnet mask included"""

    ip_address_list: List[str]


class FileList(BaseModel):
    """List of files"""

    file_list: List[str]


class CompareTTLFiles(BaseModel):
    """TTL Files to compare"""

    ttl_1: str
    ttl_2: str

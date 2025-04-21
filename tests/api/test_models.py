import pytest
from pydantic import ValidationError

from grasshopper.serializers import (
    IPAddress,
    IPAddressList,
    FileList,
    CompareTTLFiles,
    MessageResponse,
    ErrorResponse,
    FileUploadResponse
)


def test_ip_address_model():
    """Test IPAddress model validation"""
    # Valid IP addresses
    valid_ips = [
        "192.168.1.1",
        "10.0.0.1/24",
        "2001:db8::1",
        "fe80::1%eth0"
    ]
    
    for ip in valid_ips:
        model = IPAddress(ip_address=ip)
        assert model.ip_address == ip
    
    # Model should accept any string for flexibility
    # but in real usage we would add more specific validation


def test_ip_address_list_model():
    """Test IPAddressList model validation"""
    ip_list = ["192.168.1.1", "10.0.0.1/24", "172.16.0.1"]
    model = IPAddressList(ip_address_list=ip_list)
    assert model.ip_address_list == ip_list
    
    # Empty list should be valid
    model = IPAddressList(ip_address_list=[])
    assert model.ip_address_list == []
    
    # Non-list should fail
    with pytest.raises(ValidationError):
        IPAddressList(ip_address_list="not a list")
    
    # List of non-strings should fail
    with pytest.raises(ValidationError):
        IPAddressList(ip_address_list=[1, 2, 3])


def test_file_list_model():
    """Test FileList model validation"""
    file_list = ["file1.ttl", "file2.ttl", "file3.ttl"]
    model = FileList(file_list=file_list)
    assert model.file_list == file_list
    
    # Empty list should be valid
    model = FileList(file_list=[])
    assert model.file_list == []
    
    # Non-list should fail
    with pytest.raises(ValidationError):
        FileList(file_list="not a list")
    
    # List of non-strings should fail
    with pytest.raises(ValidationError):
        FileList(file_list=[1, 2, 3])


def test_compare_ttl_files_model():
    """Test CompareTTLFiles model validation"""
    model = CompareTTLFiles(ttl_1="file1.ttl", ttl_2="file2.ttl")
    assert model.ttl_1 == "file1.ttl"
    assert model.ttl_2 == "file2.ttl"
    
    # Missing fields should fail
    with pytest.raises(ValidationError):
        CompareTTLFiles(ttl_1="file1.ttl")
    
    with pytest.raises(ValidationError):
        CompareTTLFiles(ttl_2="file2.ttl")
    
    # Empty strings are allowed by default but could be validated further
    model = CompareTTLFiles(ttl_1="", ttl_2="")
    assert model.ttl_1 == ""
    assert model.ttl_2 == ""


def test_message_response_model():
    """Test MessageResponse model validation"""
    model = MessageResponse(message="Test message")
    assert model.message == "Test message"
    
    # Missing message should fail
    with pytest.raises(ValidationError):
        MessageResponse()
    
    # Empty string is valid
    model = MessageResponse(message="")
    assert model.message == ""


def test_error_response_model():
    """Test ErrorResponse model validation"""
    model = ErrorResponse(error="Test error")
    assert model.error == "Test error"
    
    # Missing error should fail
    with pytest.raises(ValidationError):
        ErrorResponse()
    
    # Empty string is valid
    model = ErrorResponse(error="")
    assert model.error == ""


def test_file_upload_response_model():
    """Test FileUploadResponse model validation"""
    model = FileUploadResponse(message="File uploaded", file_path="/path/to/file")
    assert model.message == "File uploaded"
    assert model.file_path == "/path/to/file"
    
    # Missing fields should fail
    with pytest.raises(ValidationError):
        FileUploadResponse(message="File uploaded")
    
    with pytest.raises(ValidationError):
        FileUploadResponse(file_path="/path/to/file")
    
    # Empty strings are valid
    model = FileUploadResponse(message="", file_path="")
    assert model.message == ""
    assert model.file_path == ""
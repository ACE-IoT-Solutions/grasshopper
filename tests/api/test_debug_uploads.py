"""Utility tests for debugging file upload issues.

This module contains tests specifically designed to diagnose issues with file uploads.
They're not run as part of the regular test suite but can be run manually when
troubleshooting file upload problems.
"""

import os
import sys
from io import BytesIO
import pytest


@pytest.mark.debug
def test_file_upload_diagnostics(api_client):
    """Diagnostic test for file uploads using different approaches.

    This test tries different methods of uploading files to help diagnose issues
    with file uploads. It's marked with 'debug' so it's not run in regular testing.
    Run it explicitly with: pytest tests/api/test_debug_uploads.py::test_file_upload_diagnostics -v
    """
    client, _ = api_client

    # Test file parameters
    file_content = b"test ttl content"
    filename = "test_upload.ttl"

    # Approach 1: Standard files dict
    response1 = client.post(
        "/operations/ttl",
        files={"file": (filename, file_content, "application/octet-stream")},
    )
    print(f"\nApproach 1 - Standard files dict")
    print(f"Status: {response1.status_code}")
    print(f"Response: {response1.content}")

    # Approach 2: File-like object with name
    file = BytesIO(file_content)
    file.name = filename
    response3 = client.post("/operations/ttl", files={"file": file})
    print(f"\nApproach 2 - File-like object with name")
    print(f"Status: {response3.status_code}")
    print(f"Response: {response3.content}")

    # Approach 3: Multiple parts form
    from fastapi import FastAPI, File, Request, UploadFile
    from fastapi.testclient import TestClient

    # Create a minimal test app with just the file upload endpoint
    app = FastAPI()

    @app.post("/test_upload")
    async def test_upload(request: Request, file: UploadFile = File(...)):
        return {"filename": file.filename, "content_type": file.content_type}

    with TestClient(app) as test_client:
        response = test_client.post(
            "/test_upload",
            files={"file": (filename, file_content, "application/octet-stream")},
        )
        print(f"\nApproach 3 - Minimal test app")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.content}")

    # Print summary
    print("\nDiagnostic Summary:")
    print(f"- Standard method works: {response1.status_code == 201}")
    print(f"- File-like object works: {response3.status_code == 201}")

    # This assert allows the test to be run without failing
    # Remove this line if you want it to fail to see all output
    assert True, "Diagnostic complete"

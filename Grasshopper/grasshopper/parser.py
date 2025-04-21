"""Parser models for FastAPI"""
from fastapi import UploadFile, File, Form, Depends

# No need for explicit parsers with FastAPI - we use the built-in dependencies
# This file is kept for backward compatibility
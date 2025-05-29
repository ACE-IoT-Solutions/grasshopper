"""Serializers for API"""
from flask_restx import fields
from grasshopper.restplus import api

ip_address = api.model(
    "IP Address with subnet mask",
    {
        "ip_address": fields.String(readOnly=True, description="IP address with subnet mask")
    }
)

ip_address_list = api.model(
    "List of IP addresses with subnet mask included",
    {
        "ip_address_list": fields.List(fields.String())
    }
)

file_list = api.model(
    "List of files",
    {
        "file_list": fields.List(fields.String())
    }
)

compare_ttl_files = api.model(
    "TTL Files to compare",
    {
        "ttl_1": fields.String(),
        "ttl_2": fields.String()
    }
)
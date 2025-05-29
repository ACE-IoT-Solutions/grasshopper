from flask import Blueprint
from flask_restx import Api

blueprint = Blueprint("api", __name__)
api = Api(
    app=blueprint,
    title="Grasshopper API",
    description="Manage the detection of devices in Bacnet"
)
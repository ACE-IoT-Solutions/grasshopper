from flask_restx import reqparse

file_upload_parser = reqparse.RequestParser()
file_upload_parser.add_argument('file', type='FileStorage', location='files', required=True, help='Upload a file')

from flask import Flask, abort, redirect, send_from_directory, url_for

from .api import api as operations_api
from .restplus import api, blueprint


class Config(object):
    HOST = "127.0.0.1"
    PORT = "5000"
    SERVER_NAME = f"{HOST}:{PORT}"

class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    SERVER_NAME = None
    ENV = "development"
    DEBUG = True
    # HOST = "127.0.0.1"
    # PORT = "5001"
    # SERVER_NAME = f"{HOST}:{PORT}"

def create_app(config_class=None):
    app = Flask(__name__, static_folder='dist/assets', template_folder='dist')
    config_class_obj = globals().get(config_class)
    if not config_class_obj:
        app.config.from_object(DevelopmentConfig)
        print(f"Config class '{config_class}' not found.")
    else:
        app.config.from_object(config_class_obj)

    @app.route('/')
    def index():
        return send_from_directory('dist', 'index.html')

    @app.route('/<path:path>')
    def catch_all(path):
        if path.startswith('api'):
            abort(404)
        return redirect(url_for('index'))
    
    @app.after_request
    def apply_security_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*' #'http://100.100.200.78:5174'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains'
        response.headers['Content-Security-Policy'] = f"default-src 'self'; \
            script-src 'self' 'unsafe-inline';\
            style-src 'self' 'unsafe-inline';\
            img-src 'self' data:; \
            connect-src 'self' 'unsafe-inline'; \
            worker-src 'self'; \
            object-src 'none'; \
            base-uri 'self';"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    api.add_namespace(operations_api)
    app.register_blueprint(blueprint, url_prefix="/api")
    app.api = operations_api
    return app

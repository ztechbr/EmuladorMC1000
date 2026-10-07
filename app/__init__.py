def create_app():
    from flask import Flask
    app=Flask(__name__)
    from app.controllers.main import bp
    app.register_blueprint(bp)
    return app

from flask import Flask

from config import BASE_DIR, Config
from app.models import document_metadata as db


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config.from_object(Config)
    db.init_db()

    from app.routes.auth_routes import bp as auth_bp
    from app.routes.chat_routes import bp as chat_bp
    from app.routes.document_routes import bp as doc_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(doc_bp)
    return app

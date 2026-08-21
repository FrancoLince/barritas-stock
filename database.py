import os
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def _database_uri(app):
    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url:
        # Some providers still return the old postgres:// scheme.
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        return database_url

    # Local development fallback. Vercel's filesystem is ephemeral, so
    # production should always set DATABASE_URL to a persistent PostgreSQL DB.
    db_dir = os.path.join(app.root_path, "database")
    os.makedirs(db_dir, exist_ok=True)
    return "sqlite:///" + os.path.join(db_dir, "stock.db")


def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri(app)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

from app import app, db

with app.app_context():
    db.drop_all()    # Elimina todas las tablas existentes
    db.create_all()  # Crea todas las tablas desde cero

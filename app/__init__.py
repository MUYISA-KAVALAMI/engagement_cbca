from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import datetime
db = SQLAlchemy()
login_manager = LoginManager()

from .models import Utilisateur

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'cbca-vulumbi-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cbca.db'

    db.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)

    # Import des routes à l'intérieur de la fonction pour éviter l'import circulaire
    from .routes import main
    app.register_blueprint(main)
    
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    login_manager.login_view = 'main.login'

    return app

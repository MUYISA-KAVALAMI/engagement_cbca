from app import create_app, db
from app.models import Utilisateur

app = create_app()
with app.app_context():
    # Vérifie si l'utilisateur existe déjà
    if not Utilisateur.query.filter_by(username='admin').first():
        user = Utilisateur(
            username='admin',
            email='admin@cbca.com',
            role='admin'
        )
        user.set_password('1234')  # Mot de passe de test
        db.session.add(user)
        db.session.commit()
        print("Utilisateur admin créé avec succès !")
    else:
        print("L'utilisateur admin existe déjà.")
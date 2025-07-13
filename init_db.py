from app import app, db
from models import User, Membre, Engagement, Paiement
from datetime import datetime, timedelta

def init_database():
    with app.app_context():
        # Créer les tables
        db.create_all()
        
        # Ajouter un admin par défaut
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Ajouter des données de test (optionnel)
        if not Membre.query.first():
            # Ajouter un membre exemple
            membre = Membre(
                code_membre="CBCA-VUL-001",
                nom="Jean KABILA",
                telephone="+243810000001",
                email="jean.kabila@example.com",
                adresse="Quartier Vulumbi, Butembo",
                date_naissance=datetime(1985, 5, 15).date(),
                sexe="M"
            )
            db.session.add(membre)
            
            # Ajouter un engagement
            engagement = Engagement(
                membre_id=1,
                montant_total=500.0,
                date_limite=datetime.now().date() + timedelta(days=30),
                description="Engagement pour projet construction"
            )
            db.session.add(engagement)
            
            # Ajouter un paiement
            paiement = Paiement(
                membre_id=1,
                engagement_id=1,
                montant=200.0,
                mode_paiement="mobile_money",
                reference="MTN-123456",
                enregistre_par=1
            )
            db.session.add(paiement)
        
        db.session.commit()
        print("Base de données initialisée avec succès!")

if __name__ == '__main__':
    init_database()
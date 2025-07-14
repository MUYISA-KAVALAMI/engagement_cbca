from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin

# Modèles de données
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Membre(db.Model):
    __tablename__ = 'membres'
    id = db.Column(db.Integer, primary_key=True)
    code_membre = db.Column(db.String(20), unique=True)
    nom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20),nullable=False)
    adresse = db.Column(db.String(200))
    date_naissance = db.Column(db.Date)
    sexe = db.Column(db.String(10))
    date_adhesion = db.Column(db.Date, default=datetime.utcnow().date)
    photo_profil = db.Column(db.String(255))
    statut = db.Column(db.String(20), default='Actif') # Actif, Inactif, Suspendu
    derniere_cotisation = db.Column(db.Date)
    apikey_callmebot = db.Column(db.String(255)) # Clé API CallMeBot pour WhatsApp
    
    engagements = db.relationship('Engagement', backref='membre', lazy=True)
    notifications = db.relationship('Notification', backref='membre', lazy=True)

    def is_active(self):
        return self.statut == 'Actif'
    
    def calculate_age(self):
        today = date.today()
        return today.year - self.date_naissance.year - ((today.month, today.day) < (self.date_naissance.month, self.date_naissance.day))
    
    def serialize(self):
        return {
            'id': self.id,
            'code_membre': self.code_membre,
            'nom': self.nom,
            'telephone': self.telephone,
            'adresse': self.adresse,
            'date_naissance': self.date_naissance.isoformat() if self.date_naissance else None,
            'sexe': self.sexe,
            'date_adhesion': self.date_adhesion.isoformat() if self.date_adhesion else None,
            'photo_profil': self.photo_profil,
            'statut': self.statut,
            'derniere_cotisation': self.derniere_cotisation.isoformat() if self.derniere_cotisation else None,
            'apikey_callmebot': self.apikey_callmebot
        }

class Engagement(db.Model):
    __tablename__ = 'engagements'
    id = db.Column(db.Integer, primary_key=True)
    membre_id = db.Column(db.Integer, db.ForeignKey('membres.id'), nullable=False)
    type_engagement = db.Column(db.String(50), nullable=False) # Ex: "Dîme", "Offrande spéciale", "Vœu", "Construction"
    montant_total = db.Column(db.Float, nullable=False)
    date_engagement = db.Column(db.DateTime, default=datetime.utcnow)
    date_limite = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200))
    statut = db.Column(db.String(20), default='En cours')

    paiements = db.relationship('Paiement', backref='engagement', lazy=True)

    def montant_restant(self):
        """Montant restant à ce jour"""
        return self.montant_total - sum(p.montant for p in self.paiements)

    def montant_restant_au(self, date_reference):
        return self.montant_total - sum(p.montant for p in self.paiements if p.date_paiement <= date_reference)


class Paiement(db.Model):
    __tablename__ = 'paiements'
    id = db.Column(db.Integer, primary_key=True)
    engagement_id = db.Column(db.Integer, db.ForeignKey('engagements.id'), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    date_paiement = db.Column(db.Date, default=datetime.utcnow)
    
    preuves_paiement = db.relationship('PreuvePaiement', backref='paiement', lazy=True, cascade="all, delete-orphan") # Nouvelle relation

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    membre_id = db.Column(db.Integer, db.ForeignKey('membres.id'), nullable=False)
    engagement_id = db.Column(db.Integer, db.ForeignKey('engagements.id'), nullable=True) # Peut être null si notification générale
    message = db.Column(db.String(500), nullable=False)
    date_envoi = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.String(20), default='Envoyé') # Envoyé, Échoué, Lu

# Nouveau modèle pour les preuves de paiement
class PreuvePaiement(db.Model):
    __tablename__ = 'preuves_paiement'
    id = db.Column(db.Integer, primary_key=True)
    paiement_id = db.Column(db.Integer, db.ForeignKey('paiements.id'), nullable=True) # Peut être null si la preuve est envoyée avant le paiement manuel
    membre_id = db.Column(db.Integer, db.ForeignKey('membres.id'), nullable=False) # Qui a envoyé la preuve
    chemin_photo = db.Column(db.String(255), nullable=False) # Chemin vers la photo sur le serveur
    date_soumission = db.Column(db.DateTime, default=datetime.utcnow)
    montant_declare = db.Column(db.Float) # Montant que le membre déclare avoir payé
    statut_preuve = db.Column(db.String(20), default='En attente') # En attente, Validée, Rejetée
    notes_admin = db.Column(db.String(500)) # Notes ajoutées par l'administrateur lors de la validation/rejet
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric

from . import db

from flask_login import UserMixin
from datetime import datetime

class CarteBapteme(db.Model):
    __tablename__ = 'carte_bapteme'
    idcarte = db.Column(db.Integer, primary_key=True)
    numerocarte = db.Column(db.String(50), nullable=False, unique=True)
    chapelle = db.Column(db.String(100), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    sexe = db.Column(db.String(10), nullable=False)
    datenaissance = db.Column(db.Date, nullable=False)
    lieunaissance = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(150), nullable=False)

    chretiens = db.relationship('Chretien', backref='carte_bapteme', lazy=True)


class Chretien(db.Model):
    __tablename__ = 'chretien'
    idchretien = db.Column(db.Integer, primary_key=True)
    code_chretien = db.Column(db.String(50), unique=True, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    cle_callmebot = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    idcarte = db.Column(db.Integer, db.ForeignKey('carte_bapteme.idcarte'), nullable=False)

    engagements = db.relationship('Engagement', backref='chretien', lazy=True)
    notifications = db.relationship('Notification', backref='chretien', lazy=True)


class Budget(db.Model):
    __tablename__ = 'budget'
    idbudget = db.Column(db.Integer, primary_key=True)
    exercice = db.Column(db.String(10), nullable=False)
    montanttotal = db.Column(db.Float, nullable=False)

    engagements = db.relationship('Engagement', backref='budget', lazy=True)


class Engagement(db.Model):
    __tablename__ = 'engagement'
    idengagement = db.Column(db.Integer, primary_key=True)
    date_engagement = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    montant_total = db.Column(db.Float, nullable=False)
    date_limite = db.Column(db.Date, nullable=False)
    statutengagement = db.Column(db.String(20), nullable=False, default='en cours')
    idchretien = db.Column(db.Integer, db.ForeignKey('chretien.idchretien'), nullable=False)
    idbudget = db.Column(db.Integer, db.ForeignKey('budget.idbudget'), nullable=False)

    paiements = db.relationship('Paiement', backref='engagement', lazy=True)


class Paiement(db.Model):
    __tablename__ = 'paiement'
    idpaiement = db.Column(db.Integer, primary_key=True)
    date_paiement = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    montant = db.Column(Numeric(10, 2), nullable=False)
    idengagement = db.Column(db.Integer, db.ForeignKey('engagement.idengagement'), nullable=False)

from . import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notification'
    idnotification = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    message = db.Column(db.Text)
    statut = db.Column(db.String(20))  # success ou failed
    idchretien = db.Column(db.Integer, db.ForeignKey('chretien.idchretien'))
    date_notification = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def create_success(cls, idchretien, type, message):
        notif = cls(
            idchretien=idchretien,
            type=type,
            message=message,
            statut='success'
        )
        db.session.add(notif)
        db.session.commit()

    @classmethod
    def create_failed(cls, idchretien, type, message):
        notif = cls(
            idchretien=idchretien,
            type=type,
            message=message,
            statut='failed'
        )
        db.session.add(notif)
        db.session.commit()


class Utilisateur(db.Model, UserMixin):
    __tablename__ = 'utilisateur'
    idutilisateur = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=True)  # Ajoute ce champ
    role = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        # Ajoute ici le hash du mot de passe selon ta logique
        self.password_hash = password

    def check_password(self, password):
        # Ajoute ici la vérification du mot de passe
        return self.password_hash == password

    def get_id(self):
        return str(self.idutilisateur)

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField, DecimalField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from datetime import datetime

class UtilisateurForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired()])  # Ajoute cette ligne
    role = SelectField('Rôle', choices=[('admin', 'Admin'), ('utilisateur', 'Utilisateur')], validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password', message='Les mots de passe doivent correspondre.')])
    submit = SubmitField('Enregistrer')

class ConnexionForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class CarteBaptemeForm(FlaskForm):
    numerocarte = StringField('Numéro de carte', validators=[DataRequired()])
    chapelle = SelectField('Chapelle', choices=[
        ('Vulumbe', 'Vulumbe'),
        ('Kisima', 'Kisima'),
        ('Autre', 'Autre')
    ], validators=[DataRequired()])
    nom = StringField('Nom', validators=[DataRequired()])
    prenom = StringField('Prénom', validators=[DataRequired()])
    sexe = SelectField('Sexe', choices=[
        ('M', 'Masculin'),
        ('F', 'Féminin')
    ], validators=[DataRequired()])
    datenaissance = DateField('Date de naissance', validators=[DataRequired()], format='%Y-%m-%d')
    lieunaissance = StringField('Lieu de naissance', validators=[DataRequired()])
    adresse = StringField('Adresse', validators=[DataRequired()])
    submit = SubmitField('Enregistrer')

class ChretienForm(FlaskForm):
    telephone = StringField('Téléphone', validators=[DataRequired()])
    cle_callmebot = StringField('Clé CallMeBot', validators=[DataRequired()])
    idcarte = SelectField('Carte de baptême', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enregistrer')


class EngagementForm(FlaskForm):
    montant_total = DecimalField('Montant total', validators=[DataRequired()])
    date_limite = DateField('Date limite', validators=[DataRequired()], format='%Y-%m-%d')
    idchretien = SelectField('Chrétien', coerce=int, validators=[DataRequired()])
    idbudget = SelectField('Budget', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enregistrer')
    

class PaiementForm(FlaskForm):
    montant = DecimalField('Montant', validators=[DataRequired()])
    date_paiement = DateField('Date de paiement', validators=[DataRequired()], format='%Y-%m-%d')
    idengagement = SelectField('Engagement', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enregistrer')
class NotificationForm(FlaskForm):
    type = StringField('Type', validators=[DataRequired()])
    message = StringField('Message', validators=[DataRequired()])
    idchretien = SelectField('Chrétien', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enregistrer')


class BudgetForm(FlaskForm):
    exercice = StringField('Exercice', validators=[DataRequired()])
    montanttotal = DecimalField('Montant total', validators=[DataRequired()])
    submit = SubmitField('Enregistrer')

class PaiementForm(FlaskForm):
    montant = DecimalField('Montant', places=2, validators=[DataRequired()])
    date_paiement = DateField('Date du paiement', validators=[DataRequired()], format='%Y-%m-%d', default=datetime.today)
    submit = SubmitField('Enregistrer')
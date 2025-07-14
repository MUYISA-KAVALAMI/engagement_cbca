from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from functools import wraps
from utils import envoyer_whatsapp


from extensions import db
import os, re
from datetime import datetime, timedelta, date

# 🧠 Fonction utilitaire
def telephone_valide(numero):
    return re.match(r'^\+?[0-9]{9,15}$', numero)

# ⚙️ Création de l'application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cbca.db'
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# 🛠 Initialisation des extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# ✅ Import des modèles après initialisation
with app.app_context():
    from models import User, Engagement, Paiement, Membre
    from tasks import notifier_engagements_proches

    scheduler.add_job(
        id='rappel_whatsapp',
        func=notifier_engagements_proches,
        trigger='interval',
        hours=24  # ou cron avec jour/heure
    )

    # ⚠️ Pas besoin de redéfinir engagement ici car il est déjà lié via backref 'engagement' dans Engagement



# Helpers
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generer_code_membre():
    dernier_membre = Membre.query.order_by(Membre.id.desc()).first()
    numero = 1 if not dernier_membre else dernier_membre.id + 1
    return f"CBCA-VUL-{numero:04d}"

# Configuration Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Décorateurs personnalisés
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accès réservé aux administrateurs', 'danger')
            return redirect(url_for('accueil'))
        return f(*args, **kwargs)
    return decorated_function

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Connexion réussie!', 'success')
            return redirect(url_for('accueil'))
        flash('Identifiant ou mot de passe incorrect', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))

# Routes principales
@app.route('/')
@login_required
def accueil():
    stats = {
        'total_membres': Membre.query.count(),
        'total_engagements': Engagement.query.count(),
        'engagements_actifs': Engagement.query.filter_by(statut='actif').count(),
        'paiements_mois': Paiement.query.filter(
            Paiement.date_paiement >= datetime.now() - timedelta(days=30)
        ).count(),
        'montant_mois': db.session.query(db.func.sum(Paiement.montant)).filter(
            Paiement.date_paiement >= datetime.now() - timedelta(days=30)
        ).scalar() or 0
    }
    return render_template('index.html', stats=stats)

# Gestion des membres
@app.route('/membres')
@login_required
def liste_membres():
    search = request.args.get('search', '')
    query = Membre.query
    
    if search:
        query = query.filter(Membre.nom.ilike(f'%{search}%'))
    
    membres = query.order_by(Membre.nom).all()
    return render_template('membres/liste.html', membres=membres, search=search)

@app.route('/membres/ajouter', methods=['GET', 'POST'])
@login_required
@admin_required
def ajouter_membre():
    if request.method == 'POST':
        try:
            # Validation des champs obligatoires
            if not request.form.get('nom') or not request.form.get('telephone') or not request.form.get('sexe'):
                flash('Les champs Nom, Téléphone et Sexe sont obligatoires', 'danger')
                return redirect(url_for('ajouter_membre'))
            
            if not telephone_valide(request.form.get('telephone')):
                flash("Numéro de téléphone invalide. Exemple: +243970000000", 'warning')
                return redirect(url_for('ajouter_membre'))
            # Gestion de l'upload de photo
            photo_filename = None
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename != '' and allowed_file(photo.filename):
                    photo_filename = secure_filename(photo.filename)
                    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
            
            # Conversion de la date
            date_naissance = None
            if request.form['date_naissance']:
                try:
                    date_naissance = datetime.strptime(request.form['date_naissance'], '%Y-%m-%d').date()
                except ValueError:
                    flash('Format de date invalide', 'danger')
                    return redirect(url_for('ajouter_membre'))
            
            # Création du membre
            nouveau_membre = Membre(
                code_membre=generer_code_membre(),
                nom=request.form['nom'],
                telephone=request.form['telephone'],
                adresse=request.form.get('adresse'),
                date_naissance=date_naissance,
                sexe=request.form['sexe'],
                photo=photo_filename,
                groupe=request.form.get('groupe'),
                apikey_callmebot=request.form['api'],
                statut='actif'
            )
            
            db.session.add(nouveau_membre)
            db.session.commit()
            flash('Membre ajouté avec succès!', 'success')
            return redirect(url_for('liste_membres'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout du membre: {str(e)}", 'danger')
    
    # Pour la méthode GET
    groupes = ['Chorale', 'Jeunesse', 'Dames', 'Hommes', 'Enfants']
    return render_template('membres/ajouter.html', groupes=groupes)

@app.route('/membres/<int:id>/modifier', methods=['POST'])
@login_required
@admin_required
def modifier_membre(id):
    membre = Membre.query.get_or_404(id)
    try:
        # Champs obligatoires
        nom = request.form.get('nom')
        telephone = request.form.get('telephone')
        sexe = request.form.get('sexe')

        if not nom or not telephone or not sexe:
            flash("Nom, Téléphone et Sexe sont obligatoires", "danger")
            return redirect(url_for('liste_membres'))

        # Vérification format du téléphone
        import re
        def telephone_valide(numero):
            return re.match(r'^\+?[0-9]{9,15}$', numero)

        if not telephone_valide(telephone):
            flash("Numéro de téléphone invalide", "warning")
            return redirect(url_for('liste_membres'))

        # Mise à jour des infos
        membre.nom = nom
        membre.telephone = telephone
        membre.sexe = sexe
        membre.adresse = request.form.get('adresse')
        membre.groupe = request.form.get('groupe')
        membre.apikey_callmebot = request.form.get('api')

        # Conversion de date
        date_naissance = request.form.get('date_naissance')
        if date_naissance:
            try:
                membre.date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d').date()
            except ValueError:
                flash("Format de date invalide", "danger")
                return redirect(url_for('liste_membres'))

        # Gestion de la photo
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '' and allowed_file(photo.filename):
                if membre.photo:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], membre.photo))
                    except:
                        pass
                photo_filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                membre.photo = photo_filename

        db.session.commit()
        flash("Membre modifié avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la modification : {str(e)}", "danger")

    return redirect(url_for('liste_membres'))
@app.template_filter('format_currency')
def format_currency(value):
    return f"{value:.2f} $" if value is not None else "—"

@app.template_filter('age')
def age(birthdate):
    if not birthdate:
        return "—"
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def calculer_age(date_naissance):
    today = date.today()
    return today.year - date_naissance.year - (
        (today.month, today.day) < (date_naissance.month, date_naissance.day)
    )

@app.route('/membres/<int:id>')
@login_required
def detail_membre(id):
    # 🔍 Récupération du membre
    membre = Membre.query.get_or_404(id)

    # 📆 Engagements triés par échéance
    engagements = Engagement.query.filter_by(membre_id=id)\
                   .order_by(Engagement.date_limite.asc()).all()

    # 💳 Paiements liés au membre via les engagements
    paiements = Paiement.query.join(Engagement)\
                .filter(Engagement.membre_id == id)\
                .order_by(Paiement.date_paiement.desc()).all()

    # 📊 Statistiques
    total_paiements = sum(p.montant for p in paiements)
    engagements_actifs = sum(1 for e in engagements if e.statut == 'actif')
    engagements_termines = sum(1 for e in engagements if e.statut == 'payé')

    # 🧠 Calcul de l’âge
    age = calculer_age(membre.date_naissance)

    return render_template(
        'membres/detail.html',
        membre=membre,
        engagements=engagements,
        paiements=paiements,
        total_paiements=total_paiements,
        engagements_actifs=engagements_actifs,
        engagements_termines=engagements_termines,
        age=age,
        date=date.today()
    )


# Initialisation de la base de données
def init_db():
    with app.app_context():
        db.create_all()
        # Créer le dossier uploads s'il n'existe pas
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        # Créer un admin par défaut si aucun utilisateur n'existe
        if not User.query.first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        
from datetime import datetime
from collections import defaultdict
@login_required
@app.route('/engagements')
def liste_engagements():
    engagements = Engagement.query.all()
    
    # Calcul des statistiques
    stats = defaultdict(int)
    total = len(engagements)
    
    for engagement in engagements:
        if engagement.statut == 'payé':
            stats['paid'] += 1
        elif engagement.statut == 'échu':
            stats['overdue'] += 1
        else:
            stats['in_progress'] += 1
    
    # Calcul des pourcentages
    if total > 0:
        stats['paid_percent'] = (stats['paid'] / total) * 100
        stats['overdue_percent'] = (stats['overdue'] / total) * 100
        stats['in_progress_percent'] = (stats['in_progress'] / total) * 100
    else:
        stats['paid_percent'] = 0
        stats['overdue_percent'] = 0
        stats['in_progress_percent'] = 0
    
    return render_template('engagements/liste.html', 
                         engagements=engagements,
                          now=date.today(),
                         stats=stats)

@app.route('/engagements/ajouter', methods=['GET', 'POST'])
@login_required
@admin_required
def ajouter_engagement():
    if request.method == 'POST':
        try:
            membre_id = request.form.get('membre_id')
            montant_str = request.form.get('montant')
            date_str = request.form.get('date_limite')
            description = request.form.get('description', '').strip()

            # 🔍 Validation du membre
            membre = Membre.query.get(membre_id)
            if not membre:
                flash("Membre introuvable", "danger")
                return redirect(url_for('ajouter_engagement'))

            # 🔢 Validation du montant
            try:
                montant = float(montant_str)
                if montant <= 0:
                    raise ValueError("Montant invalide")
            except (ValueError, TypeError):
                flash("Le montant doit être un nombre positif", "warning")
                return redirect(url_for('ajouter_engagement'))

            # 🗓️ Validation de la date
            try:
                date_limite = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                flash("Format de date incorrect", "danger")
                return redirect(url_for('ajouter_engagement'))

            # ✅ Création de l'engagement
            nouvel_engagement = Engagement(
                membre_id=membre_id,
                montant_total=montant,
                date_limite=date_limite,
                description=description
            )
            db.session.add(nouvel_engagement)
            db.session.commit()

            # 📲 Envoi WhatsApp (optionnel)
            if membre.apikey_callmebot:
                from utils import envoyer_whatsapp 
                message = f"Bonjour {membre.nom}, vous avez un nouvel engagement de {montant:.2f} $ à régler avant le {date_limite.strftime('%d/%m/%Y')}."
                envoyer_whatsapp(membre.telephone, membre.apikey_callmebot, message)

            flash('Engagement ajouté avec succès!', 'success')
            return redirect(url_for('liste_engagements'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur: {str(e)}", 'danger')

    membres = Membre.query.order_by(Membre.nom).all()
    return render_template('engagements/ajouter.html', membres=membres,datetime=datetime)

@app.route('/engagements/<int:id>/modifier', methods=['POST'])
@login_required
@admin_required
def modifier_engagement(id):
    engagement = Engagement.query.get_or_404(id)
    try:
        montant_str = request.form.get('montant_total')
        date_str = request.form.get('date_limite')
        description = request.form.get('description', '').strip()
        statut = request.form.get('statut', 'en cours')

        # 🔢 Validation du montant
        try:
            montant = float(montant_str)
            if montant <= 0:
                raise ValueError("Montant invalide")
        except (ValueError, TypeError):
            flash("Le montant doit être un nombre positif", "warning")
            return redirect(url_for('liste_engagements'))

        # 🗓️ Validation de la date
        try:
            date_limite = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash("Date invalide", "danger")
            return redirect(url_for('liste_engagements'))

        # ✏️ Mise à jour de l'engagement
        engagement.montant_total = montant
        engagement.date_limite = date_limite
        engagement.description = description
        engagement.statut = statut

        db.session.commit()
        
        flash("Engagement modifié avec succès", "success")

        
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la modification : {str(e)}", "danger")

    return redirect(url_for('liste_engagements'))

@app.route('/paiements')
@login_required
def liste_paiements():
    paiements = Paiement.query.order_by(Paiement.date_paiement.desc()).all()
    return render_template('paiements/liste.html', paiements=paiements,date=date)
@app.route('/paiements/<int:id>/modifier', methods=['POST'])
@login_required
@admin_required
def modifier_paiement(id):
    paiement = Paiement.query.get_or_404(id)
    try:
        montant = float(request.form.get('montant'))
        date_str = request.form.get('date_paiement')

        if montant <= 0:
            flash("Montant invalide", "warning")
            return redirect(url_for('liste_paiements'))

        try:
            paiement.date_paiement = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            flash("Date incorrecte", "danger")
            return redirect(url_for('liste_paiements'))

        paiement.montant = montant
        db.session.commit()
        flash("Paiement modifié avec succès", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")

    return redirect(url_for('liste_paiements'))

@app.route('/paiements/<int:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_paiement(id):
    paiement = Paiement.query.get_or_404(id)
    try:
        db.session.delete(paiement)
        db.session.commit()
        flash("Paiement supprimé avec succès", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    return redirect(url_for('liste_paiements'))

@app.route('/paiements/ajouter', methods=['GET', 'POST'])
@login_required
@admin_required
def ajouter_paiement():
    if request.method == 'POST':
        try:
            engagement_id = request.form.get('engagement_id')
            montant_str = request.form.get('montant')
            date_str = request.form.get('date_paiement')

            # 🔍 Validation de l'engagement
            engagement = Engagement.query.get(engagement_id)
            if not engagement:
                flash("Engagement introuvable", "danger")
                return redirect(url_for('ajouter_paiement'))

            # 🔢 Validation du montant
            try:
                montant = float(montant_str)
                if montant <= 0:
                    raise ValueError("Montant invalide")
            except:
                flash("Montant invalide", "warning")
                return redirect(url_for('ajouter_paiement'))

            # 🗓️ Validation de la date
            try:
                date_paiement = datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                date_paiement = datetime.utcnow().date()

            paiement = Paiement(
                engagement_id=engagement_id,
                montant=montant,
                date_paiement=date_paiement
            )

            db.session.add(paiement)
            db.session.commit()

            # 📲 Notification WhatsApp
            membre = engagement.membre
            if membre.apikey_callmebot:
                from utils import envoyer_whatsapp
                msg = f"Bonjour {membre.nom}, votre paiement de {montant:.2f}$ a été enregistré pour l’engagement prévu le {engagement.date_limite.strftime('%d/%m/%Y')}."
                envoyer_whatsapp(membre.telephone, membre.apikey_callmebot, msg)

            flash("Paiement enregistré avec succès!", "success")
            return redirect(url_for('liste_paiements'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur: {str(e)}", "danger")

    engagements = Engagement.query.order_by(Engagement.date_limite).all()
    return render_template('paiements/ajouter.html', engagements=engagements,date=date)

@app.route('/test-job')
def test_job():
    from tasks import notifier_engagements_proches
    notifier_engagements_proches()
    return "✅ Job exécuté manuellement"

# Route individuelle
@app.route('/notifier/engagement/<int:id>', methods=['POST'])
@login_required
def notifier_membre_engagement(id):
    engagement = Engagement.query.get_or_404(id)
    membre = engagement.membre
    msg = f"Bonjour {membre.nom}, votre engagement de {engagement.montant_total:.2f}$ expire le {engagement.date_limite.strftime('%d/%m/%Y')}. Solde restant : {engagement.montant_restant():.2f}$."
    envoyer_whatsapp(membre.telephone, membre.apikey_callmebot, msg)
    flash("Notification envoyée.", "success")
    return redirect(url_for('liste_engagements'))

# Route globale
@app.route('/notifier/tous', methods=['GET'])
@login_required
def notifier_tous_membres():
    engagements = Engagement.query.filter(Engagement.statut != 'payé').all()
    for e in engagements:
        membre = e.membre
        if membre.apikey_callmebot and membre.telephone:
            msg = f"Bonjour {membre.nom}, votre engagement de {e.montant_total:.2f}$ expire le {e.date_limite.strftime('%d/%m/%Y')}. Solde restant : {e.montant_restant():.2f}$."
            envoyer_whatsapp(membre.telephone, membre.apikey_callmebot, msg)
    flash("Tous les membres débiteurs ont été notifiés.", "info")
    return redirect(url_for('liste_engagements'))


if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
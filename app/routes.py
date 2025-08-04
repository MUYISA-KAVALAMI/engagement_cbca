from .models import Utilisateur, db, CarteBapteme, Chretien, Engagement, Budget, Paiement, Notification
from .forms import UtilisateurForm, ConnexionForm, CarteBaptemeForm, ChretienForm,  BudgetForm, EngagementForm, PaiementForm
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import random, string, requests
from decimal import Decimal

main = Blueprint('main', __name__)

def generer_code_chretien():
    suffixe = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CHR-{datetime.now().year}-{suffixe}"

def envoyer_whatsapp(numero, cle, message):
    url = f"https://api.callmebot.com/whatsapp.php?phone={numero}&text={message}&apikey={cle}"
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        print("Erreur CallMeBot:", e)
        return False

@main.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('main.login'))
    return redirect(url_for('main.home'))

@main.route('/home')
@login_required
def home():
    return render_template('home.html')

@main.route('/utilisateurs', methods=['GET', 'POST'])
@login_required
def utilisateurs():
    if current_user.role != 'admin':
        flash("Accès réservé à l'administrateur.", "danger")
        return redirect(url_for('main.home'))
    form = UtilisateurForm()
    if request.method == 'POST':
        # Si c'est une modification (le champ caché edit_id est présent)
        if 'edit_id' in request.form:
            user = Utilisateur.query.get(int(request.form['edit_id']))
            user.username = request.form['edit_username']
            user.email = request.form['edit_email']
            user.role = request.form['edit_role']
            if request.form['edit_password']:
                user.set_password(request.form['edit_password'])
            db.session.commit()
            flash('Utilisateur modifié avec succès!', 'success')
            return redirect(url_for('main.utilisateurs'))
        else:
            # Ajout d'utilisateur classique
            if form.validate_on_submit():
                user = Utilisateur(
                    username=form.username.data,
                    email=form.email.data,
                    role=form.role.data
                )
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                flash('Utilisateur ajouté avec succès!', 'success')
                return redirect(url_for('main.utilisateurs'))
    utilisateurs = Utilisateur.query.all()
    return render_template('utilisateurs.html', form=form, utilisateurs=utilisateurs)

@main.route('/utilisateur/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_utilisateur(id):
    user = Utilisateur.query.get_or_404(id)
    form = UtilisateurForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('Utilisateur modifié avec succès!', 'success')
        return redirect(url_for('main.utilisateurs'))
    return render_template('modifier_utilisateur.html', form=form, user=user)

@main.route('/utilisateur/supprimer/<int:id>', methods=['POST'])
def supprimer_utilisateur(id):
    user = Utilisateur.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Utilisateur supprimé avec succès!', 'success')
    return redirect(url_for('main.utilisateurs'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    form = ConnexionForm()
    if form.validate_on_submit():
        user = Utilisateur.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie.', 'success')
    return redirect(url_for('main.login'))

@main.route('/cartes', methods=['GET', 'POST'])
@login_required
def cartes():
    form = CarteBaptemeForm()
    if form.validate_on_submit():
        carte = CarteBapteme(
            numerocarte=form.numerocarte.data,
            chapelle=form.chapelle.data,
            nom=form.nom.data,
            prenom=form.prenom.data,
            sexe=form.sexe.data,
            datenaissance=form.datenaissance.data,
            lieunaissance=form.lieunaissance.data,
            adresse=form.adresse.data
        )
        db.session.add(carte)
        db.session.commit()
        flash('Carte de baptême ajoutée avec succès!', 'success')
        return redirect(url_for('main.cartes'))
    cartes = CarteBapteme.query.all()
    return render_template('cartes.html', form=form, cartes=cartes)

@main.route('/cartes/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_carte(id):
    carte = CarteBapteme.query.get_or_404(id)
    carte.numerocarte = request.form['edit_numerocarte']
    carte.chapelle = request.form['edit_chapelle']
    carte.nom = request.form['edit_nom']
    carte.prenom = request.form['edit_prenom']
    carte.sexe = request.form['edit_sexe']
    # Conversion ici :
    carte.datenaissance = datetime.strptime(request.form['edit_datenaissance'], '%Y-%m-%d').date()
    carte.lieunaissance = request.form['edit_lieunaissance']
    carte.adresse = request.form['edit_adresse']
    db.session.commit()
    flash('Carte modifiée avec succès!', 'success')
    return redirect(url_for('main.cartes'))

@main.route('/cartes/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_carte(id):
    carte = CarteBapteme.query.get_or_404(id)
    db.session.delete(carte)
    db.session.commit()
    flash('Carte supprimée avec succès!', 'success')
    return redirect(url_for('main.cartes'))

@main.route('/membres', methods=['GET', 'POST'])
@login_required
def membres():
    form = ChretienForm()
    form.idcarte.choices = [(c.idcarte, f"{c.numerocarte} - {c.nom} {c.prenom}") for c in CarteBapteme.query.all()]
    if form.validate_on_submit():
        code = generer_code_chretien()
        membre = Chretien(
            code_chretien=code,
            telephone=form.telephone.data,
            cle_callmebot=form.cle_callmebot.data,
            idcarte=form.idcarte.data
        )
        db.session.add(membre)
        db.session.commit()
        message = f"Bienvenue à la CBCA VULUMBI ! Votre code membre est : {code}"
        envoyer_whatsapp(membre.telephone, membre.cle_callmebot, message)
        flash('Membre ajouté et message WhatsApp envoyé !', 'success')
        return redirect(url_for('main.membres'))
    membres = Chretien.query.all()
    cartes = CarteBapteme.query.all()
    return render_template('membres.html', form=form, membres=membres, cartes=cartes)

@main.route('/membres/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_membre(id):
    membre = Chretien.query.get_or_404(id)
    membre.telephone = request.form['edit_telephone']
    membre.cle_callmebot = request.form['edit_cle_callmebot']
    membre.idcarte = int(request.form['edit_idcarte'])
    db.session.commit()
    flash('Membre modifié avec succès!', 'success')
    return redirect(url_for('main.membres'))

@main.route('/membres/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_membre(id):
    membre = Chretien.query.get_or_404(id)
    db.session.delete(membre)
    db.session.commit()
    flash('Membre supprimé avec succès!', 'success')
    return redirect(url_for('main.membres'))


def envoyer_whatsapp(numero, cle, message):
    if not numero or not cle:
        return False
        
    # Nettoyer le numéro de téléphone (enlever les espaces, +, etc.)
    numero = ''.join(filter(str.isdigit, numero))
    
    # Encoder le message pour URL
    from urllib.parse import quote
    message_encode = quote(message)
    
    url = f"https://api.callmebot.com/whatsapp.php?phone={numero}&text={message_encode}&apikey={cle}"
    
    try:
        headers = {
            'User-Agent': 'CBCA Engagement App'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"Erreur CallMeBot - Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Erreur de connexion à CallMeBot: {str(e)}")
        return False
    

@main.route('/engagements', methods=['GET', 'POST'])
@login_required
def engagements():
    form = EngagementForm()
    form.idchretien.choices = [(c.idchretien, f"{c.code_chretien} - {c.carte_bapteme.nom} {c.carte_bapteme.prenom}") 
                             for c in Chretien.query.all()]
    form.idbudget.choices = [(b.idbudget, f"{b.exercice} - {b.montanttotal}") 
                           for b in Budget.query.all()]
    
    if form.validate_on_submit():
        chretien = Chretien.query.get(form.idchretien.data)
        budget = Budget.query.get(form.idbudget.data)
        
        engagement = Engagement(
            montant_total=form.montant_total.data,
            date_limite=form.date_limite.data,
            idchretien=form.idchretien.data,
            idbudget=form.idbudget.data
        )
        
        db.session.add(engagement)
        db.session.commit()
        
        # Envoi WhatsApp
        if chretien.telephone and chretien.cle_callmebot:
            message = (
                f"*Nouvel Engagement CBCA VULUMBI*\n\n"
                f"Cher(e) {chretien.carte_bapteme.prenom},\n\n"
                f"Un nouvel engagement a été enregistré :\n"
                f"• Montant: {form.montant_total.data} USD\n"
                f"• Date limite: {form.date_limite.data.strftime('%d/%m/%Y')}\n"
                f"• Référence: ENG-{engagement.idengagement}\n\n"
                "Merci pour votre contribution!"
            )
            
            if envoyer_whatsapp(chretien.telephone, chretien.cle_callmebot, message):
                flash('Engagement enregistré et notification envoyée!', 'success')
            else:
                flash('Engagement enregistré mais échec d\'envoi WhatsApp', 'warning')
        else:
            flash('Engagement enregistré (coordonnées WhatsApp manquantes)', 'info')
        
        return redirect(url_for('main.engagements'))
    
    engagements = Engagement.query.all()
    return render_template('engagements.html', form=form, engagements=engagements)


@main.route('/engagements/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_engagement(id):
    engagement = Engagement.query.get_or_404(id)
    engagement.montant_total = request.form['edit_montant_total']
    engagement.date_limite = datetime.strptime(request.form['edit_date_limite'], '%Y-%m-%d').date()
    engagement.idchretien = int(request.form['edit_idchretien'])
    engagement.idbudget = int(request.form['edit_idbudget'])
    db.session.commit()
    flash('Engagement modifié avec succès!', 'success')
    return redirect(url_for('main.engagements'))

@main.route('/engagements/supprimer/<int:id>', methods=['POST'])
@main.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    form = BudgetForm()
    if form.validate_on_submit():
        budget = Budget(
            exercice=form.exercice.data,
            montanttotal=form.montanttotal.data
        )
        db.session.add(budget)
        db.session.commit()
        flash('Budget ajouté avec succès!', 'success')
        return redirect(url_for('main.budgets'))
    budgets = Budget.query.all()
    return render_template('budgets.html', form=form, budgets=budgets)

@main.route('/budgets/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_budget(id):
    budget = Budget.query.get_or_404(id)
    budget.exercice = request.form['edit_exercice']
    budget.montanttotal = request.form['edit_montanttotal']
    db.session.commit()
    flash('Budget modifié avec succès!', 'success')
    return redirect(url_for('main.budgets'))

@main.route('/engagements/<int:id>/paiements', methods=['GET', 'POST'])
@login_required
def voir_paiements(id):
    engagement = Engagement.query.get_or_404(id)
    chretien = engagement.chretien
    form = PaiementForm()
    form.date_paiement.data = datetime.today().date()

    if form.validate_on_submit():
        try:
            montant = Decimal(str(form.montant.data))
            total_paye = sum(p.montant for p in engagement.paiements)
            reste_a_payer = Decimal(str(engagement.montant_total)) - total_paye

            # Validation du montant
            if montant <= 0:
                flash("Le montant doit être positif", "danger")
                return redirect(url_for('main.voir_paiements', id=id))
                
            if montant > reste_a_payer:
                flash(f"Le montant ne peut pas dépasser {reste_a_payer} USD (reste à payer)", "danger")
                return redirect(url_for('main.voir_paiements', id=id))

            # Enregistrement du paiement
            paiement = Paiement(
                montant=montant,
                date_paiement=form.date_paiement.data,
                idengagement=id
            )
            db.session.add(paiement)
            
            # Mise à jour du statut
            nouveau_total = total_paye + montant
            engagement.statutengagement = 'payé' if nouveau_total >= Decimal(str(engagement.montant_total)) else 'en cours'
            
            db.session.commit()

            # Notification WhatsApp
            message = (
                f"*CBCA VULUMBI - Paiement Reçu*\n\n"
                f"Cher {chretien.carte_bapteme.prenom},\n\n"
                f"Nous avons reçu {montant} USD\n"
                f"Sur engagement ENG-{engagement.idengagement}\n"
                f"Total payé: {nouveau_total}/{engagement.montant_total} USD\n"
                f"Reste: {max(Decimal('0'), reste_a_payer - montant)} USD\n\n"
                "Merci pour votre contribution!"
            )

            if chretien.telephone and chretien.cle_callmebot:
                if envoyer_whatsapp(chretien.telephone, chretien.cle_callmebot, message):
                    Notification.create_success(chretien.idchretien, "paiement", message)
                    flash("Paiement enregistré et notification envoyée", "success")
                else:
                    Notification.create_failed(chretien.idchretien, "paiement", message)
                    flash("Paiement enregistré mais échec d'envoi WhatsApp", "warning")
            else:
                flash("Paiement enregistré (pas de notification - coordonnées manquantes)", "info")

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur: {str(e)}", "danger")

        return redirect(url_for('main.voir_paiements', id=id))

    # Affichage
    paiements = Paiement.query.filter_by(idengagement=id).order_by(Paiement.date_paiement.desc()).all()
    total_paye = sum(p.montant for p in paiements)
    reste_a_payer = max(Decimal(str(engagement.montant_total)) - total_paye, Decimal('0'))

    return render_template('paiements.html',
                         engagement=engagement,
                         paiements=paiements,
                         form=form,
                         total_paye=total_paye,
                         reste_a_payer=reste_a_payer,
                         solde_max=reste_a_payer)  # Passer le solde maximum au template

@main.route('/paiement/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_paiement(id):
    paiement = Paiement.query.get_or_404(id)
    engagement = paiement.engagement
    chretien = engagement.chretien

    try:
        ancien_montant = paiement.montant
        montant = Decimal(str(request.form['montant']))
        date_paiement = datetime.strptime(request.form['date_paiement'], '%Y-%m-%d').date()

        total_sans_celui_ci = sum(p.montant for p in engagement.paiements if p.idpaiement != paiement.idpaiement)
        nouveau_total = total_sans_celui_ci + montant

        if montant <= 0:
            flash("Le montant doit être positif.", "danger")
        elif nouveau_total > engagement.montant_total:
            flash(f"Le montant total dépasserait l'engagement ({engagement.montant_total} USD).", "danger")
        else:
            paiement.montant = montant
            paiement.date_paiement = date_paiement
            engagement.statutengagement = 'payé' if nouveau_total >= engagement.montant_total else 'en cours'
            db.session.commit()

            # Notification WhatsApp
            message = (
                f"*CBCA VULUMBI - Paiement Modifié*\n\n"
                f"Bonjour {chretien.carte_bapteme.prenom},\n"
                f"Votre paiement a été modifié :\n"
                f"• Ancien montant : {ancien_montant} USD\n"
                f"• Nouveau montant : {montant} USD\n"
                f"• Date : {date_paiement.strftime('%d/%m/%Y')}\n"
                f"• Engagement ENG-{engagement.idengagement}\n\n"
                f"Total payé : {nouveau_total}/{engagement.montant_total} USD"
            )

            if chretien.telephone and chretien.cle_callmebot:
                if envoyer_whatsapp(chretien.telephone, chretien.cle_callmebot, message):
                    Notification.create_success(chretien.idchretien, "modification paiement", message)
                    flash("Paiement modifié et notification envoyée.", "success")
                else:
                    Notification.create_failed(chretien.idchretien, "modification paiement", message)
                    flash("Paiement modifié, mais échec d'envoi WhatsApp.", "warning")
            else:
                flash("Paiement modifié (pas de numéro WhatsApp).", "info")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")

    return redirect(url_for('main.voir_paiements', id=engagement.idengagement))

@main.route('/paiement/supprimer/<int:id>', methods=['GET'])
@login_required
def supprimer_paiement(id):
    paiement = Paiement.query.get_or_404(id)
    engagement = paiement.engagement
    chretien = engagement.chretien

    montant_supprime = paiement.montant
    date_paiement = paiement.date_paiement.strftime('%d/%m/%Y')

    db.session.delete(paiement)
    db.session.commit()

    # Recalcul du statut
    total_apres = sum(p.montant for p in engagement.paiements)
    engagement.statutengagement = 'payé' if total_apres >= engagement.montant_total else 'en cours'
    db.session.commit()

    # 🔔 Message WhatsApp
    message = (
        f"*CBCA VULUMBI - Paiement Supprimé*\n\n"
        f"Bonjour {chretien.carte_bapteme.prenom},\n\n"
        f"Le paiement de {montant_supprime} USD effectué le {date_paiement} a été supprimé.\n"
        f"• Engagement : ENG-{engagement.idengagement}\n"
        f"• Nouveau total payé : {total_apres}/{engagement.montant_total} USD\n\n"
        f"Merci pour votre attention."
    )

    if chretien.telephone and chretien.cle_callmebot:
        if envoyer_whatsapp(chretien.telephone, chretien.cle_callmebot, message):
            Notification.create_success(chretien.idchretien, "suppression paiement", message)
            flash("Paiement supprimé et notification envoyée.", "success")
        else:
            Notification.create_failed(chretien.idchretien, "suppression paiement", message)
            flash("Paiement supprimé mais échec d'envoi WhatsApp.", "warning")
    else:
        flash("Paiement supprimé (pas de notification : numéro manquant).", "info")

    return redirect(url_for('main.voir_paiements', id=engagement.idengagement))



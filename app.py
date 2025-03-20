import eventlet
 eventlet.monkey_patch()
 eventlet.monkey_patch()  # Doit être appelé avant tout autre import !
 
 from flask import Flask, request, jsonify, send_file
 from flask import Flask, request, jsonify, send_file, Blueprint, session
 from flask_socketio import SocketIO
 from collections import deque, OrderedDict
 import qrcode
 import io
 import qrcode, io
 
 app = Flask(__name__)
 app.config['SECRET_KEY'] = 'secret!'
 app.config['SECRET_KEY'] = 'secret!'  # Clé nécessaire pour utiliser les sessions
 socketio = SocketIO(app, async_mode='eventlet')
 
 # Variables globales
 # Variables globales partagées
 waiting_list = deque(range(1, 3001))      # Liste d'attente des numéros disponibles
 registered_queue = deque()                # File d'attente des participants inscrits via QR code
 active_counters = OrderedDict()           # Dernier numéro appelé par chaque comptoir
 
 # ------------------------------
 # Routes pour l'enregistrement
 # ------------------------------
 # --- Blueprint pour l'enregistrement via QR code ---
 register_bp = Blueprint('register', __name__)
 
 @app.route('/qr')
 @register_bp.route('/qr')
 def generate_qr():
     """
     Génère un QR code pointant vers l'endpoint /register.
 @@ -33,68 +32,76 @@ def generate_qr():
     buf.seek(0)
     return send_file(buf, mimetype='image/png')
 
 @app.route('/register', methods=['GET'])
 @register_bp.route('/register', methods=['GET'])
 def register():
     """
     Endpoint pour l'enregistrement via QR code.
     Attribue un numéro au participant et met à jour la file d'attente.
     Conserve le numéro en session pour que, en cas de rafraîchissement, l'utilisateur retrouve le même numéro.
     """
     if waiting_list:
         number = waiting_list.popleft()
         registered_queue.append(number)
         print("Nouveau participant enregistré : numéro", number)
         socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
         return f"""
         <!DOCTYPE html>
         <html lang="fr">
         <head>
             <meta charset="utf-8">
             <title>Numéro attribué</title>
             <style>
                 body {{
                     font-family: Arial, sans-serif;
                     text-align: center;
                     margin: 0;
                     padding: 50px;
                 }}
                 h1 {{
                     font-size: 80px;
                     margin-bottom: 20px;
                     color: #2c3e50;
                 }}
                 p {{
                     font-size: 20px;
                     color: #555;
                 }}
             </style>
         </head>
         <body>
             <h1>{number}</h1>
             <p>Système de file d'attente développé par Simon Guy, Directeur TI de la SRA</p>
         </body>
         </html>
         """
     if 'assigned_number' in session:
         number = session['assigned_number']
     else:
         return """
         <!DOCTYPE html>
         <html lang="fr">
         <head>
             <meta charset="utf-8">
             <title>Aucun numéro disponible</title>
         </head>
         <body style="text-align:center;padding:50px;">
             <h1 style="color:red;">Plus aucun numéro disponible</h1>
         </body>
         </html>
         """, 404
         if waiting_list:
             number = waiting_list.popleft()
             registered_queue.append(number)
             session['assigned_number'] = number  # Enregistrement du numéro en session
             print("Nouveau participant enregistré : numéro", number)
             socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
         else:
             return """
             <!DOCTYPE html>
             <html lang="fr">
             <head>
                 <meta charset="utf-8">
                 <title>Aucun numéro disponible</title>
             </head>
             <body style="text-align:center;padding:50px;">
                 <h1 style="color:red;">Plus aucun numéro disponible</h1>
             </body>
             </html>
             """, 404
 
 # ------------------------------
 # Routes principales de l'application
 # ------------------------------
     return f"""
     <!DOCTYPE html>
     <html lang="fr">
     <head>
         <meta charset="utf-8">
         <title>Numéro attribué</title>
         <style>
             body {{
                 font-family: Arial, sans-serif;
                 text-align: center;
                 margin: 0;
                 padding: 50px;
             }}
             h1 {{
                 font-size: 150px; /* Numéro affiché en très grand */
                 margin-bottom: 20px;
                 color: #2c3e50;
             }}
             p {{
                 font-size: 30px; /* Texte plus grand */
                 color: #555;
             }}
         </style>
     </head>
     <body>
         <h1>{number}</h1>
         <p>Système de file d'attente développé par Simon Guy, Directeur TI de la SRA</p>
     </body>
     </html>
     """
 
 # Enregistrer le blueprint dans l'application
 app.register_blueprint(register_bp)
 
 # --- Routes principales de l'application ---
 
 @app.route('/')
 def home():
     # Générer dynamiquement des liens pour 60 comptoirs
     """
     Page d'accueil avec des liens vers 60 comptoirs, l'affichage en direct et le QR code d'enregistrement.
     """
     liens = "".join(f'<li><a href="/counter/{i}">Comptoir {i}</a></li>' for i in range(1, 61))
     return f"""
     <!DOCTYPE html>
 @@ -155,7 +162,9 @@ def home():
 
 @app.route('/counter/<int:counter_id>', methods=['GET'])
 def counter_page(counter_id):
     # Page dédiée à un comptoir avec bouton pour appeler le prochain participant inscrit
     """
     Page dédiée à un comptoir avec un bouton pour appeler le prochain participant.
     """
     return f"""
     <!DOCTYPE html>
     <html>
 @@ -239,6 +248,9 @@ def counter_page(counter_id):
 
 @app.route('/next', methods=['POST'])
 def next_client():
     """
     Endpoint appelé par un comptoir pour récupérer le prochain numéro.
     """
     print("File actuelle:", list(registered_queue))
     data = request.get_json()
     counter = data.get('counter')
 @@ -258,6 +270,9 @@ def next_client():
 
 @app.route('/display', methods=['GET'])
 def display():
     """
     Affichage en direct des derniers numéros appelés et de la file d'attente.
     """
     items = list(reversed(active_counters.items()))
     html = """
     <!DOCTYPE html>
 @@ -304,7 +319,7 @@ def display():
                 text-decoration: underline;
             }
         </style>
         <!-- Charger la bibliothèque client Socket.IO -->
         <!-- Charger Socket.IO côté client -->
         <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.min.js"></script>
     </head>
     <body>

#!/usr/bin/env python
import eventlet
eventlet.monkey_patch()  # Doit être appelé avant tout autre import !

from flask import Flask, request, jsonify, send_file, Blueprint, session
from flask_socketio import SocketIO
from collections import deque, OrderedDict
import qrcode, io
import random

# On indique à Flask que le dossier statique est "sstatic" et accessible via /static
app = Flask(__name__, static_folder='sstatic', static_url_path='/static')
app.config['SECRET_KEY'] = 'secret!'  # Clé nécessaire pour utiliser les sessions
socketio = SocketIO(app, async_mode='eventlet')

# Variables globales partagées
waiting_list = deque(range(1, 3001))      # Liste d'attente des numéros disponibles
registered_queue = deque()               # File d'attente des participants inscrits via QR code
active_counters = OrderedDict()          # Dernier numéro appelé par chaque comptoir

# --- Blueprint pour l'enregistrement via QR code ---
register_bp = Blueprint('register', __name__)

@register_bp.route('/qr')
def generate_qr():
    """
    Génère un QR code pointant vers l'endpoint /register.
    Remplacez l'URL par celle de votre serveur (IP publique ou nom de domaine).
    """
    url = "http://147.93.40.205:5000/register"  # Exemple d'URL, à adapter
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@register_bp.route('/register', methods=['GET'])
def register():
    """
    Endpoint pour l'enregistrement via QR code.
    Conserve le numéro en session pour que, en cas de rafraîchissement,
    l'utilisateur retrouve le même numéro.

    Affiche un fond d'écran choisi aléatoirement et un logo SRA en haut à gauche.
    """
    # Sélection aléatoire d'une image parmi celles du dossier sstatic
    images = ["images.png", "images (1).png", "images.jpeg"]
    chosen_image = random.choice(images)

    if 'assigned_number' in session:
        number = session['assigned_number']
    else:
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
                background: url('/static/{chosen_image}') no-repeat center center fixed;
                background-size: cover;
                position: relative;
            }}
            /* Logo SRA noir en haut à gauche */
            .logo {{
                position: absolute;
                top: 10px;
                left: 10px;
                width: 150px;
                z-index: 999;
            }}
            h1 {{
                font-size: 150px; /* Numéro affiché en très grand */
                margin-bottom: 20px;
                color: #2c3e50;
                margin-top: 100px; /* Pour laisser de l'espace au logo */
            }}
            p {{
                font-size: 30px; /* Texte plus grand */
                color: #555;
            }}
        </style>
    </head>
    <body>
        <img src="/static/sra_black.png" alt="Logo SRA" class="logo" />
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
    """
    Page d'accueil avec un logo SRA (blanc) et des liens vers 60 comptoirs.
    """
    liens = "".join(f'<li><a href="/counter/{i}">Comptoir {i}</a></li>' for i in range(1, 61))
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accueil - Système de File d'Attente</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f9f9f9;
                position: relative;
            }}
            /* Logo SRA HEC (blanc) en haut à gauche */
            .logo {{
                position: absolute;
                top: 10px;
                left: 10px;
                width: 200px;
                z-index: 999;
            }}
            h1 {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                text-align: center;
                margin-top: 0;
            }}
            .container {{
                max-width: 800px;
                margin: 80px auto 20px; /* Laisser de la place pour le logo */
                background: #fff;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                margin-bottom: 10px;
                font-size: 16px;
            }}
            a {{
                text-decoration: none;
                color: #2980b9;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <img src="/static/sra_hec.png" alt="Logo SRA HEC" class="logo" />
        <h1>Système de File d'Attente</h1>
        <div class="container">
            <p>Bienvenue ! Ce système vous permet de gérer une file d'attente et d'appeler le prochain numéro depuis n'importe quel comptoir.</p>
            <p><a href="/display">Voir l'affichage en direct des comptoirs</a></p>
            <p><a href="/qr">Afficher le QR code pour s'enregistrer</a></p>
            <h2>Liste des Comptoirs</h2>
            <ul>
                {liens}
            </ul>
        </div>
    </body>
    </html>
    """

@app.route('/counter/<int:counter_id>', methods=['GET'])
def counter_page(counter_id):
    """
    Page dédiée à un comptoir, avec un logo SRA noir en haut à gauche.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comptoir {counter_id}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f9f9f9;
                position: relative;
            }}
            .logo {{
                position: absolute;
                top: 10px;
                left: 10px;
                width: 150px;
                z-index: 999;
            }}
            h1 {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                text-align: center;
                margin-top: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 80px auto 20px;
                background: #fff;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            #callNextBtn {{
                padding: 10px 20px;
                background: #2980b9;
                color: #fff;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }}
            #callNextBtn:hover {{
                background: #1f6390;
            }}
            #result {{
                margin-top: 20px;
                font-size: 18px;
                color: #333;
            }}
            a {{
                text-decoration: none;
                color: #2980b9;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <img src="/static/sra_black.png" alt="Logo SRA" class="logo" />
        <h1>Comptoir {counter_id}</h1>
        <div class="container">
            <p>Cliquez sur le bouton ci-dessous pour appeler le prochain participant inscrit.</p>
            <button id="callNextBtn">Appeler le prochain numéro</button>
            <div id="result"></div>
            <p><a href="/">Retour à l'accueil</a></p>
        </div>
        <script>
            document.getElementById('callNextBtn').addEventListener('click', function() {{
                fetch('/next', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{counter: 'Comptoir {counter_id}'}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.error) {{
                        document.getElementById('result').innerText = data.error;
                    }} else {{
                        document.getElementById('result').innerText = 'Numéro appelé pour ' + data.counter + ' : ' + data.number;
                    }}
                }})
                .catch(err => console.error(err));
            }});
        </script>
    </body>
    </html>
    """

@app.route('/next', methods=['POST'])
def next_client():
    """
    Endpoint appelé par un comptoir pour récupérer le prochain numéro.
    """
    print("File actuelle:", list(registered_queue))
    data = request.get_json()
    counter = data.get('counter')
    if not counter:
        return jsonify({'error': "L'identifiant du comptoir est requis"}), 400

    if registered_queue:
        next_number = registered_queue.popleft()
        active_counters[counter] = next_number
        active_counters.move_to_end(counter, last=True)
        print("Appel du numéro pour", counter, ":", next_number)
        socketio.emit('update', {'active_counters': list(active_counters.items())})
        socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
        return jsonify({'status': 'appelé', 'counter': counter, 'number': next_number})
    else:
        return jsonify({'error': 'Aucun participant en attente'}), 404

@app.route('/display', methods=['GET'])
def display():
    """
    Affichage en direct des derniers numéros appelés et de la file d'attente,
    avec le logo Clinique d'impôts HEC Montréal en haut à gauche.
    """
    items = list(reversed(active_counters.items()))
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Affichage en Direct des Comptoirs</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f9f9f9;
                position: relative;
            }}
            .logo {{
                position: absolute;
                top: 10px;
                left: 10px;
                width: 200px;
                z-index: 999;
            }}
            h1 {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 10px;
                text-align: center;
                margin-top: 0;
            }}
            .container {{
                max-width: 800px;
                margin: 80px auto 20px;
                background: #fff;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                margin: 10px 0;
                font-size: 18px;
            }}
            .empty {{
                color: #888;
                font-style: italic;
            }}
            a {{
                text-decoration: none;
                color: #2980b9;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
        <!-- Charger Socket.IO côté client -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.min.js"></script>
    </head>
    <body>
        <img src="/static/hec_clinique.png" alt="Logo Clinique d'impôts" class="logo" />
        <h1>Affichage en Direct des Comptoirs</h1>
        <div class="container">
            <div id="countersList">
    """
    if items:
        html += "<ul>"
        for counter, number in items:
            html += f"<li><strong>{counter}</strong> : Numéro {number}</li>"
        html += "</ul>"
    else:
        html += "<p class='empty'>Aucun numéro appelé pour le moment.</p>"
    
    html += """
            </div>
            <h2>File d'attente des participants</h2>
            <div id="queueList"></div>
            <p><a href="/">Retour à l'accueil</a></p>
        </div>
        <script>
            var socket = io();
            socket.on('connect', function() {{
                console.log("Connecté à Socket.IO !");
            }});
            socket.on('update', function(data) {{
                console.log("Événement update reçu :", data);
                var items = data.active_counters.slice().reverse();
                var html = "<ul>";
                items.forEach(function(item) {{
                    html += "<li><strong>" + item[0] + "</strong> : Numéro " + item[1] + "</li>";
                }});
                html += "</ul>";
                document.getElementById('countersList').innerHTML = html;
            }});
            socket.on('update_queue', function(data) {{
                console.log("Mise à jour de la file d'attente :", data);
                var queue = data.registered_queue;
                var html = "";
                if(queue.length > 0) {{
                    html = "<ul>";
                    queue.forEach(function(number) {{
                        html += "<li>Numéro " + number + "</li>";
                    }});
                    html += "</ul>";
                }} else {{
                    html = "<p class='empty'>Aucun participant en attente.</p>";
                }}
                document.getElementById('queueList').innerHTML = html;
            }});
        </script>
    </body>
    </html>
    """
    return html

@app.route('/test-emit')
def test_emit():
    socketio.emit('update', {'active_counters': list(active_counters.items())})
    socketio.emit('update_queue', {'registered_queue': list(registered_queue)})
    return "Événement de test émis !"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
